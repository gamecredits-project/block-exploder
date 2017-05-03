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


def only_one(function=None, key="", timeout=None):
    """Enforce only one celery task at a time."""

    def _dec(run_func):
        """Decorator."""

        def _caller(*args, **kwargs):
            """Caller."""
            ret_value = None
            have_lock = False
            lock = REDIS_CLIENT.lock(key, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = run_func(*args, **kwargs)
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        return _caller

    return _dec(function) if function is not None else _dec


class SyncTask(Task):
    @only_one(key="SingleTask", timeout=60 * 60)
    def run(self, **kwargs):
        client = MongoClient()
        database = MongoDatabaseGateway(client.exploder)
        blockchain = Blockchain(database)

        blocks_dir = "/home/vagrant/.gamecredits/blocks"
        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (RPC_USER, RPC_PASSWORD))
        syncer = BlockchainSyncer(database, blockchain, blocks_dir, rpc_client)
        syncer.sync_auto()


app = Celery('tasks', broker='redis://localhost:6379/0')
app.conf.result_backend = 'redis://localhost:6379/0'
app.tasks.register(SyncTask)

app.conf.beat_schedule = {
    'sync-every-10-seconds': {
        'task': 'tasks.SyncTask',
        'schedule': 10.0,
    },
}

app.conf.timezone = 'UTC'
