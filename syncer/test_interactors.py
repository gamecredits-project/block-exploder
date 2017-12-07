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

    def get_old_price(self):
        pass

    # def get_old_btc_price(self, timestamp_min, timestamp_max):
    #     self.db.price_history.find(
    #         {'timestamp':{'$gte':timestamp_min, '$lte': timestamp_max}})

    def test_get_reponse(self):
        response = requests.get(self.config.get('syncer', 'game_price_url'))
        json_data = json.loads(response.text)[0]

        # coinmarket_info = {}
        # if json_data:
        #     coinmarket_info['price_usd'] = json_data['price_usd']
        #     coinmarket_info['price_btc'] = json_data['price_btc']
        #     coinmarket_info['24h_volume_usd'] = json_data['24h_volume_usd']
        #     coinmarket_info['market_cap_usd'] = json_data['market_cap_usd']
        #     coinmarket_info['total_supply'] = json_data['total_supply']
        #     coinmarket_info['percent_change_24h_usd'] = json_data['percent_change_24h']

        # # Retuns tuple
        # print coinmarket_info

        # old_price = 100

        # Hocemo da pronadjemo u testu zadnju cenu za 10 minuta
        # 10 minuta je 600 sekundi duuuh, delta time za eventualnu gresku
        # ako celery nije upisao odmah je 1 minut tj. 60 sekundi

        client = MongoClient()
        database = MongoDatabaseGateway(client.exploder, self.config)
        coinmarketcap_analizer = CoinmarketcapAnalyzer(database, self.config)

        new_price = json_data['price_btc']
        new_price_time = int(time.time())
        old_price_time = new_price_time

        old_price = coinmarketcap_analizer.get_old_btc_price(old_price_time)
        old_price = max(old_price)


        new_price = Decimal(new_price)
        # u'0.0001196', u'0.00012298'


        print new_price
        print old_price


        if new_price == old_price:
            return 0
        try:
            getcontext().prec = 3
            change_percent = ((new_price-old_price)/old_price)*Decimal(100)
            print float(change_percent)
        except ZeroDivisionError:
            return 0


    def get_graph_api_coinmarketcap(self):
        coinmarketcap_api = 'https://graphs.coinmarketcap.com/currencies/gamecredits/1409590461000/1512672849000/'

        response = requests.get(coinmarketcap_api)
        response_json = response.json()

        client = MongoClient()
        database = MongoDatabaseGateway(client.exploder, self.config)
        coinmarketcap_analizer = CoinmarketcapAnalyzer(database, self.config)

        # USD HISTORY
        price_history_usd = response_json['price_usd']
        print 'Lenght of the array: %s' %(len(price_history_usd))

        usd_history_list = []
        timestamp_list = []
        for i in range(len(price_history_usd)):

            in_depth_list = price_history_usd[i]
            usd_history_list.append(Decimal(in_depth_list[1]))
            timestamp_list.append(in_depth_list[0])
            # print 'Timestamp: %s Volume in USD: %s' %(in_depth_list[0], Decimal(in_depth_list[1]))

        print "BTC first element {}".format(usd_history_list[0])

        # BTC HISTORY
        price_history_btc = response_json['price_btc']
        print 'Lenght of the array: %s' %(len(price_history_btc))

        btc_history_list = []
        for i in range(len(price_history_btc)):

            in_depth_list = price_history_btc[i]
            btc_history_list.append(Decimal(in_depth_list[1]))
            # print 'Timestamp: %s Price BTC: %s' %(in_depth_list[0], Decimal(in_depth_list[1]))

        print "USD first element {}".format(btc_history_list[0])
        # # VOLUME HISTORY
        # volume_history = response_json['volume_usd']
        # print 'Lenght of the array: %s' %(len(volume_history))
        #
        #
        # for i in range(len(volume_history)):
        #
        #     in_depth_list = volume_history[i]
        #     print 'Timestamp: %s Volume in USD: %s' %(in_depth_list[0], in_depth_list[1])

        # MARKETCAP HISTORY
        marketcap_history = response_json['market_cap_by_available_supply']
        print 'Lenght of the array: %s' %(len(marketcap_history))

        marketcap_history_list = []
        for i in range(len(marketcap_history)):

            in_depth_list = marketcap_history[i]
            marketcap_history_list.append(Decimal(in_depth_list[1]))
            # print 'Timestamp: %s Marketcap in USD: %s' %(in_depth_list[0], in_depth_list[1])

        print "Marketcap first element {}".format(marketcap_history_list[0])

        for i in range(len(timestamp_list)):
            print usd_history_list[i]
            print btc_history_list[i]
            print marketcap_history_list[i]
            print "OVO JE VREME! {}".format(timestamp_list[i])
            coinmarketcap_analizer.save_price_history(
                    float(usd_history_list[i]), float(btc_history_list[i]),
                    float(marketcap_history_list[i]), float(str(timestamp_list[i])[:-3])
            )

if __name__ == '__main__':
    unittest.main()
