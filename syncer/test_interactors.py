import unittest
import copy
import os
import ConfigParser
from mock import MagicMock
from interactors import Blockchain
from test_gateways import generate_test_data
from gateways import get_mongo_connection, MongoDatabaseGateway
from serializers import BlockSerializer, TransactionSerializer


class InsertBlockTestCaseWithMocking(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        CONFIG_FILE = os.environ['EXPLODER_CONFIG']
        self.config = ConfigParser.RawConfigParser()
        self.config.read(CONFIG_FILE)

    def setUp(self):
        self.db = MagicMock()
        self.chain = Blockchain(self.db, self.config)
        self.example_block = generate_test_data(1, self.config)[0]

    def test_chain_peak_is_none_should_create_coinbase(self):
        self.db.get_highest_block.return_value = None
        block = self.chain.insert_block(block=self.example_block)['block']

        self.assertEqual(block.height, 0)
        self.assertEqual(block.chainwork, block.work)
        self.assertEqual(block.chain, self.config.get('syncer', 'main_chain'))

    def test_append_to_main_chain(self):
        block2 = copy.deepcopy(self.example_block)
        block2.hash = "somefakehash"
        block2.previousblockhash = self.example_block.hash
        self.db.get_highest_block.return_value = self.example_block
        self.db.get_block_by_hash.return_value = self.example_block

        result = self.chain.insert_block(block2)
        added_block = result['block']

        self.assertFalse(result['fork'])
        self.assertFalse(result['reconverge'])

        self.assertEqual(added_block.height, self.example_block.height + 1)
        self.assertEqual(added_block.chainwork, self.example_block.chainwork + block2.work)
        self.assertEqual(added_block.chain, self.config.get('syncer', 'main_chain'))


class InsertBlockTestCaseWithTestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CONFIG_FILE = os.environ['EXPLODER_CONFIG']
        cls.config = ConfigParser.RawConfigParser()
        cls.config.read(CONFIG_FILE)
        cls.config.set('syncer', 'unspent_tracking', "False")

        cls.client = get_mongo_connection()
        cls.db = cls.client.test_database
        blocks = generate_test_data(50, cls.config)
        transactions = []
        for block in blocks:
            transactions += block.tx

        cls.blocks = blocks[:45]
        for block in cls.blocks:
            block.chain = cls.config.get('syncer', 'main_chain')

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

        self.chain = Blockchain(self.db_gateway, self.config)

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
        self.assertNotEqual(added['block'].chain, self.config.get('syncer', 'main_chain'))

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
        self.assertEqual(some_block_on_main_chain.chain, self.config.get('syncer', 'main_chain'))
        added = self.chain.insert_block(to_add)

        self.assertTrue(added['fork'])
        self.assertTrue(added['reconverge'])

        some_block_on_main_chain = self.db_gateway.get_block_by_hash(self.blocks[11].hash)
        self.assertNotEqual(some_block_on_main_chain.chain, self.config.get('syncer', 'main_chain'))


if __name__ == '__main__':
    unittest.main()
