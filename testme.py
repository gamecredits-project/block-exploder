from syncer.interactors import Blockchain, BlockchainSyncer
from syncer.gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
import ConfigParser
import redis

REDIS_CLIENT = redis.Redis()

config = ConfigParser.RawConfigParser()
config.read('/home/vagrant/.exploder/exploder.conf')

client = MongoClient()
database = MongoDatabaseGateway(client.exploder, config)
database.update_network_stats(supply=3421, blockchain_size=2.55)
# blockchain = Blockchain(database, config)

rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                              % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
syncer = BlockchainSyncer(database, blockchain, rpc_client, config)
syncer.sync_auto(limit=1500)
