from syncer.interactors import Blockchain, BlockchainSyncer
from syncer.gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
import ConfigParser
import redis
import time
from bson.code import Code

REDIS_CLIENT = redis.Redis()

config = ConfigParser.RawConfigParser()
config.read('/home/vagrant/.exploder/exploder.conf')

client = MongoClient()
db = client.exploder

start = time.time()
trs = db.transactions.find().limit(5000)

unspent = []
for tr in trs:
    for i, vout in enumerate(tr['vout']):
        spend = db.transactions.find_one({"vin.prev_txid": tr['txid'], "vin.vout_index": i})
        if not spend:
            unspent.append(tr)

end = time.time()
print "Num unspent: %s, time: %s" % (len(unspent), (end - start))
# trs = db.transactions.find({"vout.addresses": "GHt33DrxWodFARCsawmLrDcSA4CEx9vz44"})

# pipeline = [
#     {"$match": { "vout.addresses": "GHt33DrxWodFARCsawmLrDcSA4CEx9vz44"} },
#     {$unwind: "$vout.addresses" },
#     {$group: { _id: "$class_artist", tags: { $sum: 1 } }},
#     {$project: { _id: 0,class_artist: "$_id", tags: 1 } },
#     {$sort: { tags: -1 } }
# ]

# database = MongoDatabaseGateway(client.exploder, config)
# blockchain = Blockchain(database, config)

# rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
#                               % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
# syncer = BlockchainSyncer(database, blockchain, rpc_client, config)
# syncer.sync_auto()

# db.transactions.aggregate([
#     {$match: {"vout.addresses": "GHt33DrxWodFARCsawmLrDcSA4CEx9vz44"}},
#     {$unwind: "$vout.addresses"},
#     # {$group: { _id: "$vout.addresses", total: { $sum: "vout.value"}}}
# ])

# db.transactions.aggregate([
#     {$match: {"vout.addresses": "GKR6MHuN1zxiXXsHLSTD7Es73VA11aM4jz"}},
#     {$unwind: "$vout"},
#     {$match: {"vout.addresses": "GKR6MHuN1zxiXXsHLSTD7Es73VA11aM4jz"}},
#     {$project: { "vout.addresses": 1, "vout.value": 1}},
#     {$group: {_id: "$vout.addresses", volume: {$sum: "$vout.value"}}}
# ])
