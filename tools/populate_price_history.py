import requests
import json
from decimal import *
import ConfigParser
from pymongo import MongoClient
import os
import sys
sys.path.append('../')
from syncer.interactors import CoinmarketcapAnalyzer
from syncer.gateways import MongoDatabaseGateway

CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

def populate_price_history():
    coinmarketcap_api = 'https://graphs.coinmarketcap.com/currencies/gamecredits/1409590461000/1512672849000/'

    response = requests.get(coinmarketcap_api)
    response_json = response.json()

    client = MongoClient()
    database = MongoDatabaseGateway(client.exploder, config)
    coinmarketcap_analizer = CoinmarketcapAnalyzer(database, config)

    # USD HISTORY
    price_history_usd = response_json['price_usd']

    usd_history_list = []
    timestamp_list = []
    for i in range(len(price_history_usd)):

        in_depth_list = price_history_usd[i]
        usd_history_list.append(Decimal(in_depth_list[1]))
        timestamp_list.append(in_depth_list[0])

    # BTC HISTORY
    price_history_btc = response_json['price_btc']

    btc_history_list = []
    for i in range(len(price_history_btc)):

        in_depth_list = price_history_btc[i]
        btc_history_list.append(Decimal(in_depth_list[1]))

    # MARKETCAP HISTORY
    marketcap_history = response_json['market_cap_by_available_supply']

    marketcap_history_list = []
    for i in range(len(marketcap_history)):

        in_depth_list = marketcap_history[i]
        marketcap_history_list.append(Decimal(in_depth_list[1]))

    for i in range(len(timestamp_list)):
        coinmarketcap_analizer.save_price_history(
            float(usd_history_list[i]), float(btc_history_list[i]),
            float(marketcap_history_list[i]), float(str(timestamp_list[i])[:-3])
        )

# def delete_blocks(block_num_to_remove):
#     client = MongoClient()
#     database = MongoDatabaseGateway(client.exploder, config)
#     highest_in_db = database.blocks.find_one({"chain": 'main_chain'},
#                                              sort=[("height", -1)])
#
#     block_height = highest_in_db['height']
#
#     for i in range(block_num_to_remove):
#         removed_block = database.blocks.remove({"height": block_height-i})
#         print "== Removed block height == {} {}".format(block_height-i, removed_block)

if __name__ == '__main__':
    populate_price_history()

    # CAREFUL WITH THIS BRISE MANY BLOKOVA!
    # delete_blocks(1)
