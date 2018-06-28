import unittest
import os
import ConfigParser

from gamecredits.helpers import get_rpc_connection
from gamecredits.factories import BlockFactory
from gateways import get_mongo_connection, MongoDatabaseGateway
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer


def generate_test_data(num_blocks, config):
    rpc = get_rpc_connection(
        rpc_user=config.get('syncer', 'rpc_user'),
        rpc_password=config.get('syncer', 'rpc_password'),
        rpc_port=config.get('syncer', 'rpc_port')
    )

    block_heights = range(123321, 123321 + num_blocks)

    block_hashes = [rpc.getblockhash(height) for height in block_heights]
    rpc_blocks = [rpc.getblock(block_hash) for block_hash in block_hashes]

    blocks = []
    for block in rpc_blocks:
        block_transactions = [rpc.getrawtransaction(tx, 1) for tx in block['tx']]
        blocks.append(BlockFactory.from_rpc(block, block_transactions))

    return blocks

def generate_unspent_spent_test_data(config):
    rpc = get_rpc_connection(
        rpc_user=config.get('syncer', 'rpc_user'),
        rpc_password=config.get('syncer', 'rpc_password'),
        rpc_port=config.get('syncer', 'rpc_port')
    )

    # Unspent transaction in block height 122913
    # This transaction was spent in 123373 block
    block_heights = range(122913, 123374)
    
    block_hashes = [rpc.getblockhash(height) for height in block_heights]
    rpc_blocks = [rpc.getblock(block_hash) for block_hash in block_hashes]

    blocks = []
    for block in rpc_blocks:
        block_transactions = [rpc.getrawtransaction(tx, 1) for tx in block['tx']]
        blocks.append(BlockFactory.from_rpc(block, block_transactions))

    return blocks

class MongoDbGatewayTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CONFIG_FILE = os.environ['EXPLODER_CONFIG']
        cls.config = ConfigParser.RawConfigParser()
        cls.config.read(CONFIG_FILE)

        cls.client = get_mongo_connection()
        cls.db = cls.client.test_database
        blocks = generate_test_data(50, cls.config)

        for block in blocks:
            block.chain = cls.config.get('syncer', 'main_chain')
        transactions = []
        for block in blocks:
            transactions += block.tx

        cls.blocks = blocks[:45]
        cls.blocks_to_insert = blocks[45:]
        cls.transactions = transactions[:45]
        cls.transactions_to_insert = transactions[45:]

    @classmethod
    def tearDownClass(cls):
        cls.client.drop_database('test_database')

    def setUp(self):
        self.db.blocks.insert_many([BlockSerializer.to_database(block) for block in self.blocks])
        self.db.transactions.insert_many([TransactionSerializer.to_database(tr) for tr in self.transactions])

        self.db_gateway = MongoDatabaseGateway(
            database=self.db,
            config=self.config
        )

    def tearDown(self):
        self.db.blocks.drop()
        self.db.transactions.drop()

    def test_get_highest_block(self):
        highest_block = max(self.blocks, key=lambda block: block.height)
        self.assertEqual(highest_block, self.db_gateway.get_highest_block())

    def test_get_block_by_hash(self):
        some_block = self.blocks[13]
        fetched_block = self.db_gateway.get_block_by_hash(some_block.hash)
        self.assertEqual(some_block, fetched_block)

    def test_get_block_by_height(self):
        some_block = self.blocks[14]
        fetched_block = self.db_gateway.get_block_by_height(some_block.height)
        self.assertEqual(some_block, fetched_block)

    def test_put_block(self):
        block = self.blocks_to_insert[0]

        # Check that this block doesn't exist in the DB
        with self.assertRaises(KeyError):
            self.db_gateway.get_block_by_hash(block.hash)

        # Insert it and then check that it's there
        self.db_gateway.put_block(block)
        self.assertEqual(self.db_gateway.get_block_by_hash(block.hash), block)

    def test_delete_block(self):
        block = self.blocks[0]

        # Check that this block exists in the DB
        self.assertEqual(block, self.db_gateway.get_block_by_hash(block.hash))

        # Delete it and then check that it isn't there any more
        self.db_gateway.delete_block(block.hash)

        with self.assertRaises(KeyError):
            self.db_gateway.get_block_by_hash(block.hash)

    def test_update_block(self):
        block = self.blocks[0]

        # Check that this block exists in the DB
        self.assertEqual(block, self.db_gateway.get_block_by_hash(block.hash))

        # Delete it and then check that it isn't there any more
        self.db_gateway.update_block(block.hash, {"height": 666})

        fetched_block = self.db_gateway.get_block_by_hash(block.hash)
        self.assertEqual(fetched_block.height, 666)

    def test_get_transaction_by_txid(self):
        transaction = self.transactions[0]

        self.assertEqual(transaction, self.db_gateway.get_transaction_by_txid(transaction.txid))

    def test_get_transactions_by_blockhash(self):
        blockhash = self.transactions[0].blockhash
        transactions = [tr for tr in self.transactions if tr.blockhash == blockhash]

        fetched_transactions = self.db_gateway.get_transactions_by_blockhash(blockhash)

        self.assertEqual(len(fetched_transactions), len(transactions))

        for i in range(len(transactions)):
            self.assertEqual(transactions[i], fetched_transactions[i])

    def test_get_transactions_by_address(self):
        address = self.transactions[0].vout[0].addresses[0]
        fetched = self.db_gateway.get_transactions_by_address(address)
        self.assertGreater(len(fetched), 0)

    def test_put_transaction(self):
        transaction = self.transactions_to_insert[0]

        # Check that this block doesn't exist in the DB
        with self.assertRaises(KeyError):
            self.db_gateway.get_transaction_by_txid(transaction.txid)

        # Insert it and then check that it's there
        self.db_gateway.put_transaction(transaction)
        self.assertEqual(self.db_gateway.get_transaction_by_txid(transaction.txid), transaction)


if __name__ == "__main__":
    unittest.main()
