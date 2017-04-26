import unittest
import random

from gamecredits.helpers import get_rpc_connection
from gamecredits.factories import BlockFactory
from gamecredits.entities import Vin
from gateways import get_mongo_connection, MongoDatabaseGateway
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer


def generate_test_data(num_blocks):
    rpc = get_rpc_connection(
        rpc_user="62ca2d89-6d4a-44bd-8334-fa63ce26a1a3",
        rpc_password="CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup",
        rpc_port=8332
    )

    block_heights = range(123321, 123321 + num_blocks)

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
        cls.client = get_mongo_connection()
        cls.db = cls.client.test_database
        blocks = generate_test_data(50)
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

        for tr in self.transactions:
            self.db.vin.insert_many([VinSerializer.to_database(vin, tr.txid) for vin in tr.vin])
            list_of_lists = [VoutSerializer.to_database(vout, tr.txid, index) for (index, vout) in enumerate(tr.vout)]
            self.db.vout.insert_many([item for sublist in list_of_lists for item in sublist])

        self.db_gateway = MongoDatabaseGateway(
            database=self.db,
            cache=True,
            cache_size=5
        )

    def tearDown(self):
        self.db.blocks.drop()
        self.db.transactions.drop()
        self.db.vin.drop()
        self.db.vout.drop()

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

    def test_get_latest_blocks_without_offset(self):
        blocks = sorted(self.blocks, key=lambda block: block.height, reverse=True)[:5]
        fetched_blocks = self.db_gateway.get_latest_blocks(limit=5, offset=0)

        self.assertEqual(len(blocks), len(fetched_blocks))

        for i in range(len(fetched_blocks)):
            self.assertEqual(blocks[i], fetched_blocks[i])

    def test_get_latest_blocks_with_offset(self):
        offset = 5
        blocks = sorted(self.blocks, key=lambda block: block.height, reverse=True)[offset:offset + 5]
        fetched_blocks = self.db_gateway.get_latest_blocks(limit=5, offset=5)

        self.assertEqual(len(blocks), len(fetched_blocks))

        for i in range(len(fetched_blocks)):
            self.assertEqual(blocks[i], fetched_blocks[i])

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

    def test_get_vouts_by_address(self):
        address = self.transactions[5].vout[0].addresses[0]
        self.assertGreater(len(self.db_gateway.get_vouts_by_address(address)), 0)

    def test_get_vin_by_vout(self):
        vout = self.transactions[5].vout[0]
        vout.index = 0
        vout.txid = self.transactions[5].txid
        fake_vin = Vin(
            txid=self.transactions[7].txid,
            prev_txid=vout.txid,
            vout_index=vout.index,
            hex="xexexeex",
            sequence=1
        )
        # First we create a vin that references an existing vout
        self.db_gateway.put_vin(fake_vin, fake_vin.txid)

        self.assertEqual(fake_vin, self.db_gateway.get_vin_by_vout(vout))


if __name__ == "__main__":
    unittest.main()
