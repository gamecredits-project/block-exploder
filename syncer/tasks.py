from syncer.interactors import Blockchain, BlockchainSyncer
from syncer.gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
from celery import Celery
from celery.task import Task
import redis
import ConfigParser
import os

REDIS_CLIENT = redis.Redis()
CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)


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
    @only_one(key="SingleTask", timeout=config.getint('syncer', 'task_lock_timeout'))
    def run(self, **kwargs):
        client = MongoClient()
        database = MongoDatabaseGateway(client.exploder, config)
        blockchain = Blockchain(database, config)

        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
        syncer = BlockchainSyncer(database, blockchain, rpc_client, config)
        syncer.sync_auto()


app = Celery('tasks', broker='redis://localhost:6379/0')
app.conf.result_backend = 'redis://localhost:6379/0'
app.tasks.register(SyncTask)

app.conf.beat_schedule = {
    'sync-every-10-seconds': {
        'task': 'syncer.tasks.SyncTask',
        'schedule': 10.0,
    },
}

app.conf.timezone = 'UTC'
