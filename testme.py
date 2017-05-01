from syncer.interactors import Blockchain, BlockchainSyncer
from syncer.gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
from celery import Celery
from celery.task import Task
import redis

REDIS_CLIENT = redis.Redis()
RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"

client = MongoClient()
database = MongoDatabaseGateway(client.exploder)
blockchain = Blockchain(database)

blocks_dir = "/home/vagrant/.gamecredits/blocks"
rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                              % (RPC_USER, RPC_PASSWORD))
syncer = BlockchainSyncer(database, blockchain, blocks_dir, rpc_client)
syncer.sync_auto()
