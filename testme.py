from syncer.interactors import Blockchain, BlockchainSyncer
from syncer.gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
import ConfigParser
import redis
import time
from bson.code import Code
from exploder_api.gateways import DatabaseGateway

REDIS_CLIENT = redis.Redis()

config = ConfigParser.RawConfigParser()
config.read('/home/vagrant/.exploder/exploder.conf')

client = MongoClient()
db = client.exploder

database = DatabaseGateway(db, config)

print database.get_address_balance("GYpeCyCtHCbRqqKHwjf6w5cq4xsgYoDAgH")

# database = MongoDatabaseGateway(client.exploder, config)
# blockchain = Blockchain(database, config)

# rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
#                               % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
# syncer = BlockchainSyncer(database, blockchain, rpc_client, config)
# syncer.sync_auto()