import unittest
import copy
import os
import requests
import json
import time
import datetime
from decimal import *
import ConfigParser
from mock import MagicMock
from pymongo import MongoClient
from interactors import Blockchain, CoinmarketcapAnalyzer
from test_gateways import generate_test_data, generate_unspent_spent_test_data
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
        """
        If new mined block's previousblockhash is our highest block in the db
        we should only extend the main chain, fork shouldn't happen
        """

        # First we mock the new mined block
        block2 = copy.deepcopy(self.example_block)
        block2.hash = "somefakehash"

        # Mock the previousblockhash so it points to the highest_in_chain
        block2.previousblockhash = self.example_block.hash

        # Mock get highest block db method
        self.db.get_highest_block.return_value = self.example_block
        self.db.get_block_by_hash.return_value = self.example_block

        # Call the insert block method
        result = self.chain.insert_block(block2)
        added_block = result['block']

        # There should be no fork or reconverge
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


class InsertBlockUnspentTracking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CONFIG_FILE = os.environ['EXPLODER_CONFIG']
        cls.config = ConfigParser.RawConfigParser()
        cls.config.read(CONFIG_FILE)
        cls.config.set('syncer', 'unspent_tracking', "True")
        # Cache size is 1, because we want to insert cache to the MongoDB
        cls.config.set('syncer', 'cache_size', 1)

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

    def test_transactions_fork_no_reconverge(self):
        to_add = self.blocks_to_insert[0]

        fork_point = self.blocks[10]

        to_add.previousblockhash = fork_point.hash

        added = self.chain.insert_block(to_add)

        self.assertTrue(added['fork'])
        self.assertFalse(added['reconverge'])

        self.assertEqual(added['block'].height, fork_point.height + 1)
        # Check if the block is in the sidechain
        self.assertNotEqual(added['block'].chain, self.config.get('syncer', 'main_chain'))

        # Check the transactions in side chain block
        sidechain_tx = self.db_gateway.get_transactions_by_blockhash(added['block'].hash)

        # Transactions should be sidechain        
        for tx in sidechain_tx:
            self.assertFalse(tx.main_chain)

        # Take the next block
        to_add2 = self.blocks_to_insert[1]
        to_add2.previousblockhash = to_add.hash

        added2 = self.chain.insert_block(to_add2)

        self.assertTrue(added2['fork'])
        self.assertFalse(added2['reconverge'])

        self.assertEqual(added2['block'].height, added['block'].height + 1)
        self.assertEqual(added2['block'].chain, added['block'].chain)

        # Check the transaction in side chain block
        sidechain_tx2 = self.db_gateway.get_transactions_by_blockhash(added2['block'].hash)
        
        # Transactions should be sidechain
        for tx2 in sidechain_tx2:
            self.assertFalse(tx2.main_chain)

    def test_transactions_fork_reconverge(self):
        to_add = self.blocks_to_insert[0]
        fork_point = self.blocks[10]

        to_add.previousblockhash = fork_point.hash
        # Force reconverge
        to_add.work = 10000000000
        some_block_on_main_chain = self.db_gateway.get_block_by_hash(self.blocks[11].hash)
        # Check if block is on the main chain
        self.assertEqual(some_block_on_main_chain.chain, self.config.get('syncer', 'main_chain'))
        
        added = self.chain.insert_block(to_add)

        self.assertTrue(added['fork'])
        self.assertTrue(added['reconverge'])

        new_mainchain_transactions = self.db_gateway.get_transactions_by_blockhash(added['block'].hash)
        for new_tx in new_mainchain_transactions:
            self.assertTrue(new_tx.main_chain)

        some_block_on_main_chain = self.db_gateway.get_block_by_hash(self.blocks[11].hash)
        self.assertNotEqual(some_block_on_main_chain.chain, self.config.get('syncer', 'main_chain'))

class InsertBlockSpentTracking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        CONFIG_FILE = os.environ['EXPLODER_CONFIG']
        cls.config = ConfigParser.RawConfigParser()
        cls.config.read(CONFIG_FILE)
        cls.config.set('syncer', 'unspent_tracking', "True")
        # Cache size is 1, because we want to insert cache to the MongoDB
        cls.config.set('syncer', 'cache_size', 1)

        cls.client = get_mongo_connection()
        cls.db = cls.client.test_database
        blocks = generate_unspent_spent_test_data(cls.config)
        transactions = []
        for block in blocks:
            transactions += block.tx

        cls.blocks = blocks[:440]
        for block in cls.blocks:
            block.chain = cls.config.get('syncer', 'main_chain')
        
        cls.blocks_to_insert = blocks[440:]

        cls.transactions = transactions[:440]
        cls.transactions_to_insert = transactions[440:]

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

    def test_spent_transactions(self):
        unspent_transaction_blockhash = self.blocks[0].hash
        # First check the unspent transaction in the db
        unspent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        unspent_utxo = [vout for utxo in unspent_transaction for vout in unspent_transaction[0].vout]
        
        # Transaction should be on the mainchain
        self.assertTrue(unspent_transaction[0].main_chain)
        # This transaction should be unspent
        self.assertFalse(unspent_utxo[0].spent)

        # Add rest of the blocks to the database
        for block in self.blocks_to_insert:
            self.chain.insert_block(block)
        
        # Check again for the same unspent transaction
        spent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        spent_utxo = [vout for utxo in spent_transaction for vout in spent_transaction[0].vout]
        # Transaction should still be on the mainchain
        self.assertTrue(spent_transaction[0].main_chain)
        # This transaction has been spent
        self.assertTrue(spent_utxo[0].spent)

    def test_spent_transaction_fork_no_reconverge(self):
        unspent_transaction_blockhash = self.blocks[0].hash
        # First check the unspent transaction in the db
        unspent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        unspent_utxo = [vout for utxo in unspent_transaction for vout in unspent_transaction[0].vout]
        # Transaction should be on the mainchain
        self.assertTrue(unspent_transaction[0].main_chain)
        # This transaction should be unspent
        self.assertFalse(unspent_utxo[0].spent)

        # Insert first block to insert on the list
        to_add = self.blocks_to_insert[0]

        # Fork point is already added block
        fork_point = self.blocks[10]

        # Take the first block
        to_add.previousblockhash = fork_point.hash
        
        for block in self.blocks_to_insert:
            added = self.chain.insert_block(block)

        self.assertTrue(added['fork'])
        self.assertFalse(added['reconverge'])
        # Check if the block is in the sidechain
        self.assertNotEqual(added['block'].chain, self.config.get('syncer', 'main_chain'))

        # Check the transactions in side chain block
        sidechain_tx = self.db_gateway.get_transactions_by_blockhash(added['block'].hash)

        # Transactions should be sidechain        
        for tx in sidechain_tx:
            self.assertFalse(tx.main_chain)

        # First check the unspent transaction in the db
        spent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        spent_utxo = [vout for utxo in spent_transaction for vout in spent_transaction[0].vout]
        
        self.assertTrue(spent_utxo[0].spent)

    def test_spent_transaction_fork_reconverge(self):
        unspent_transaction_blockhash = self.blocks[0].hash
        # First check the unspent transaction in the db
        unspent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        unspent_utxo = [vout for utxo in unspent_transaction for vout in unspent_transaction[0].vout]
        # Transaction should be on the mainchain
        self.assertTrue(unspent_transaction[0].main_chain)
        # This transaction should be unspent
        self.assertFalse(unspent_utxo[0].spent)

        # Insert first block to insert on the list
        to_add = self.blocks_to_insert[0]

        # Fork point is already added block
        fork_point = self.blocks[10]

        # Take the first block
        to_add.previousblockhash = fork_point.hash
        to_add.work = 10000000000
        
        for block in self.blocks_to_insert:
            added = self.chain.insert_block(block)

        self.assertTrue(added['fork'])
        self.assertFalse(added['reconverge'])
            # Check if the block is in the sidechain
        self.assertNotEqual(added['block'].chain, self.config.get('syncer', 'main_chain'))

        # Check the transactions in side chain block
        sidechain_tx = self.db_gateway.get_transactions_by_blockhash(added['block'].hash)

        # Transactions should be sidechain        
        for tx in sidechain_tx:
            self.assertFalse(tx.main_chain)

        # First check the unspent transaction in the db
        spent_transaction = self.db_gateway.get_transactions_by_blockhash(unspent_transaction_blockhash)
        spent_utxo = [vout for utxo in spent_transaction for vout in spent_transaction[0].vout]
        
        self.assertTrue(spent_utxo[0].spent)
                
if __name__ == '__main__':
    unittest.main()
