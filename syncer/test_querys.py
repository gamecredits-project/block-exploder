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

    def get_address_transactions(self, addresses, start):
        if not start:
            self.transactions.find({"vout.addresses": {"$in": addresses}})
        list_of_transactions = []
        for address in self.transactions.find({"vout.addresses": {"$in": addresses}}):
            list_of_transactions.append(address)
        return list_of_transactions

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


    def post_addresses_volume(self, addresses):
        # Check if the address is unused on the blockchain
        if not self.transactions.find({"vout.addresses": {"$in":addresses}}):
            return 0

        pipeline = [
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": "$vout"},
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "", "volume": {"$sum":"$vout.value"}}}
        ]

        result = self.transactions.aggregate(pipeline)
        result = list(result)

        if not result:
            return 0

        return result


    def post_addresses_balance(self, addresses):
        pipeline = [
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "vout_index"}},
            {"$match": {"vout.spent": False, "vout.addresses":{"$in": addresses}}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "vout", "balance": {"$sum": "$vout.value"}}}
        ]

        # pipeline = [
        #     {"$match": {"vout.addresses": {"$in": addresses}}},
        #     {"$unwind": "$vout"},
        #     {"$match": {"vout.addresses": {"$in": addresses}}},
        #     {"$project": {"vout.addresses": 1, "vout.value": 1}},
        #     {"$group": {"_id": "", "volume": {"$sum":"$vout.value"}}}
        # ]

        result = self.transactions.aggregate(pipeline)
        result = list(result)

        # result = list(result)

        if not result:
            return 0

        return result.next()

    def post_addresses_unspent(self, addresses):
        pipeline = [
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
            {"$project": {"vout": 1, "txid": 1, "index": 1}},
            {"$match": {"vout.spent": False, "vout.addresses": {"$in": addresses}}}
        ]

        unspent = self.transactions.aggregate(pipeline)

        results = []
        for uns in unspent:
            uns['vout']['txid'] = uns['txid']
            uns['vout']['index'] = uns['index']
            results.append(uns['vout'])

        return results

    def get_address_unspent(self, address):
        unspent = self.transactions.aggregate([
            {"$match": {"vout.addresses": address}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
            {"$project": {"vout": 1, "txid": 1, "index": 1}},
            {"$match": {"vout.spent": True, "vout.addresses": address}}
        ])

        results = []
        for uns in unspent:
            uns['vout']['txid'] = uns['txid']
            uns['vout']['index'] = uns['index']
            results.append(uns['vout'])

        return results


test_gate = TestGateways(database=mongo.exploder, config=config)
#test_gate.get_address_unspent("GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq")
#test_gate.get_address_balance("GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq")
#print test_gate.get_address_transactions()
# for element in test_gate.get_address_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL"]):
#     print element

# print test_gate.get_address_num_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])
# print test_gate.get_address_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])

# print test_gate.get_address_num_transactions(["GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq","GeoGVuTQymomAyui4rwHpAWRoZnWzcNoZL","GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])
# arr = test_gate.post_addresses_unspent(["GUU68sZq86xY8rDbhma1g7uVM79uJVzygW"])
# print test_gate.get_address_volume("GN9xNC69QqxFXNLuSCRShLsorhtiSC7Xdq")
def test():
    address_hash = {
    "addresses": "string"
    }
    for key in address_hash.keys():
        if not key != config.get('syncer', 'key_for_address_post_requests'):
            print key
            print 'prosao'
        else:
            print 'racku'
test()
