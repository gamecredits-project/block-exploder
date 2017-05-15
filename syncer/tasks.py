from interactors import Blockchain, BlockchainSyncer
from gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
from celery import Celery
from celery.task import Task
from celery.schedules import crontab
import redis
import ConfigParser
import os
import raven
import logging
from raven.contrib.celery import register_signal, register_logger_signal


REDIS_CLIENT = redis.Redis()
CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)


class MyCelery(Celery):
    def on_configure(self):
        if config.getboolean('syncer', 'sentry'):
            token1 = config.get('syncer', 'sentry_token1')
            token2 = config.get('syncer', 'sentry_token2')
            path = config.get('syncer', 'sentry_path')
            sentry_url = "https://%s:%s@%s" % (token1, token2, path)
            client = raven.Client(sentry_url)

            # register a custom filter to filter out duplicate logs
            register_logger_signal(client, loglevel=logging.WARNING)

            # hook into the Celery error handler
            register_signal(client)


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


class HashrateTask(Task):
    def run(self, **kwargs):
        client = MongoClient()
        database = MongoDatabaseGateway(client.exploder, config)
        blockchain = Blockchain(database, config)

        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
        syncer = BlockchainSyncer(database, blockchain, rpc_client, config)
        syncer.calculate_network_hash_rate()


app = MyCelery('tasks', broker='redis://localhost:6379/0')
app.conf.result_backend = 'redis://localhost:6379/0'
app.tasks.register(SyncTask)
app.tasks.register(HashrateTask)

app.conf.beat_schedule = {
    'sync-every-10-seconds': {
        'task': 'syncer.tasks.SyncTask',
        'schedule': 10.0,
    },
    'hashrate-once-a-day': {
        'task': 'syncer.tasks.HashrateTask',
        'schedule': crontab(minute=0, hour=12),  # It's high noon
    },
}

app.conf.timezone = 'UTC'
