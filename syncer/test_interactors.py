import unittest
import copy
from mock import MagicMock
from interactors import Blockchain, MAIN_CHAIN
from fixtures import EXAMPLE_MONGO_BLOCK
from factories import MongoBlockFactory
from test_gateways import generate_test_data
from gateways import get_mongo_connection, MongoDatabaseGateway
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer


class InsertBlockTestCaseWithMocking(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.chain = Blockchain(self.db)
        self.example_block = MongoBlockFactory.from_mongo(EXAMPLE_MONGO_BLOCK)

    def test_chain_peak_is_none_should_create_coinbase(self):
        self.db.get_highest_block.return_value = None
        block = self.chain.insert_block(block=self.example_block)['block']

        self.assertEqual(block.height, 0)
        self.assertEqual(block.chainwork, block.work)
        self.assertEqual(block.chain, MAIN_CHAIN)
        self.assertEqual(self.chain.chain_peak, block)
        self.assertFalse(self.chain.first_iter, False)

    def test_append_to_main_chain(self):
        self.chain.chain_peak = self.example_block
        block2 = copy.deepcopy(self.example_block)
        block2.hash = "somefakehash"
        block2.previousblockhash = self.example_block.hash

        result = self.chain.insert_block(block2)
        added_block = result['block']

        self.assertFalse(result['fork'])
        self.assertFalse(result['reconverge'])

        self.assertEqual(added_block.height, self.example_block.height + 1)
        self.assertEqual(added_block.chainwork, self.example_block.chainwork + block2.work)
        self.assertEqual(added_block.chain, MAIN_CHAIN)
        self.assertEqual(self.chain.chain_peak.hash, block2.hash)


class InsertBlockTestCaseWithTestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_mongo_connection()
        cls.db = cls.client.test_database
        blocks = generate_test_data(50)
        transactions = []
        for block in blocks:
            transactions += block.tx

        cls.blocks = blocks[:45]
        for block in cls.blocks:
            block.chain = MAIN_CHAIN

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

        self.chain = Blockchain(self.db_gateway)

    def tearDown(self):
        self.db.blocks.drop()
        self.db.transactions.drop()
        self.db.vin.drop()
        self.db.vout.drop()

    def test_fork_no_reconverge(self):
        to_add = self.blocks_to_insert[0]
        fork_point = self.blocks[10]
        to_add.previousblockhash = fork_point.hash

        added = self.chain.insert_block(to_add)

        self.assertTrue(added['fork'])
        self.assertFalse(added['reconverge'])

        self.assertEqual(added['block'].height, fork_point.height + 1)
        self.assertNotEqual(added['block'].chain, MAIN_CHAIN)

        to_add2 = self.blocks_to_insert[1]
        to_add2.previousblockhash = to_add.hash

        added2 = self.chain.insert_block(to_add2)

        self.assertTrue(added2['fork'])
        self.assertFalse(added2['reconverge'])

        self.assertEqual(added2['block'].height, added['block'].height + 1)
        self.assertEqual(added2['block'].chain, added['block'].chain)

    def test_fork_reconverge(self):
        to_add = self.blocks_to_insert[0]
        fork_point = self.blocks[10]
        to_add.previousblockhash = fork_point.hash
        # Force reconverge
        to_add.work = 10000000000

        some_block_on_main_chain = self.db_gateway.get_block_by_hash(self.blocks[11].hash)
        self.assertEqual(some_block_on_main_chain.chain, MAIN_CHAIN)
        added = self.chain.insert_block(to_add)

        self.assertTrue(added['fork'])
        self.assertTrue(added['reconverge'])

        some_block_on_main_chain = self.db_gateway.get_block_by_hash(self.blocks[11].hash)
        self.assertNotEqual(some_block_on_main_chain.chain, MAIN_CHAIN)


if __name__ == '__main__':
    unittest.main()
