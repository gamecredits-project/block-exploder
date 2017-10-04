import pymongo
import sys
import os
import ConfigParser
from pymongo import MongoClient

CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

mongo = MongoClient()

class TestGateways(object):
    def __init__(self, database, config):
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vin = database.vin
        self.vout = database.vout
        self.hashrate = database.hashrate
        self.network_stats = database.network_stats
        self.sync_history = database.sync_history
        self.client_info = database.client_info
        self.config = config

    def show_me(self, element):
        print element

    def get_address_unspent(self, addresses):
        unspent = self.transactions.aggregate([
            {"$match": {"vout.addresses": {"$in":addresses}}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
            {"$project": {"vout": 1, "txid": 1, "index": 1}},
            {"$match": {"vout.spent": False, "vout.addresses": {"$in":addresses}}}
        ])

        results = []
        for uns in unspent:
            uns['vout']['txid'] = uns['txid']
            uns['vout']['index'] = uns['index']
            results.append(uns['vout'])

        return results

    def get_address_balance(self, address):
        result = self.transactions.aggregate([
            {"$match": {"vout.addresses": address}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "vout_index"}},
            {"$match": {"vout.spent": False, "vout.addresses": address}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "$vout.addresses", "balance": {"$sum": "$vout.value"}}}
        ])

        result = list(result)

        if not result:
            print 0

        print "hi"

    # def get_address_transactions(self):
    #     # if not start:
    #     return self.blocks.find({"height": {"$in": [1795109, 1795108]}})
    #
    #     # return list(self.transactions.find({"vout.addresses": address, "blocktime": {"$lte": start}})
    #                 #.sort("blocktime", pymongo.DESCENDING).limit(limit))

    def get_address_transactions(self, addresses, start):
        if not start:
            self.transactions.find({"vout.addresses": {"$in": addresses}})
        list_of_transactions = []
        for address in self.transactions.find({"vout.addresses": {"$in": addresses}}):
            list_of_transactions.append(address)
        return list_of_transactions
                    #.sort("blocktime", pymongo.DESCENDING).limit(limit))

    def get_address_num_transactions(self, address):
        pipeline = [
            {"$match": {"vout.addresses": {"$in":address}}},
            {"$project": {"vout.addresses": 1}},
            {"$group": {"_id": "vout.addresses", "num_transactions": {"$sum": 1}}}
        ]

        result = self.transactions.aggregate(pipeline)

        result = list(result)
        if not result:
            return 0

        return result[0]['num_transactions']



test_gate = TestGateways(database=mongo.exploder, config=config)
#test_gate.get_address_unspent("GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq")
#test_gate.get_address_balance("GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq")
#print test_gate.get_address_transactions()
# for element in test_gate.get_address_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL"]):
#     print element

# print test_gate.get_address_num_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])
# print test_gate.get_address_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])

print test_gate.get_address_num_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])
