from interactors import Blockchain, BlockchainSyncer, BlockchainAnalyzer,\
CoinmarketcapAnalyzer
from gateways import MongoDatabaseGateway
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
from celery import Celery
from celery.task import Task
from celery.schedules import crontab
from helpers import only_one, generate_bootstrap, get_client_ip
import ConfigParser
import os
import raven
import logging
import time
import datetime
from decimal import *
from raven.contrib.celery import register_signal, register_logger_signal


CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)


class SyncerCelery(Celery):
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


class SyncTask(Task):
    """
    Checks for new blocks and syncs the db to be up to date with the
    current state of the blockchain
    """
    @only_one(key="SingleTask", timeout=config.getint('syncer', 'task_lock_timeout'))
    def run(self, **kwargs):
        client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))
        database = MongoDatabaseGateway(client.exploder, config)
        blockchain = Blockchain(database, config)
        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))
        syncer = BlockchainSyncer(database, blockchain, rpc_client, config)

        # This is where the real work is done
        syncer.sync_auto()


class DailyTask(Task):
    @only_one(key="SingleDailyTask", timeout=config.getint('syncer', 'task_lock_timeout'))
    def run(self, **kwargs):
        client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))

        database = MongoDatabaseGateway(client.exploder, config)
        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))

        analizer = BlockchainAnalyzer(database, rpc_client, config)
        # Save hash_rate
        hash_rate = analizer.get_network_hash_rate()
        timestamp = time.time()
        analizer.save_network_hash_rate(hash_rate, timestamp)
        # Save network stats
        supply = analizer.get_supply()
        size = analizer.get_blockchain_size()
        analizer.save_network_stats(supply, size)

        # Update client info
        url = config.get('syncer', 'ipify_url')
        client_ip = get_client_ip(url)
        version = analizer.get_client_version()
        peer_info = analizer.get_peer_info()
        updated_peer_info = analizer.update_peer_location(peer_info)
        analizer.save_client_info(version, client_ip, updated_peer_info)

        bootstrap_dir = config.get('syncer', 'bootstrap_dir')
        generate_bootstrap(
            config.get('syncer', 'datadir_path'),
            bootstrap_dir
        )


class HalfMinuteTask(Task):
    @only_one(key="SingleHalfMinuteTask", timeout=config.getint('syncer', 'task_lock_timeout'))
    def run(self, **kwargs):
        client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))
        database = MongoDatabaseGateway(client.exploder, config)
        rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                      % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))

        analizer = BlockchainAnalyzer(database, rpc_client, config)
        # Calculate and save sync progress
        progress = analizer.calculate_sync_progress()
        analizer.update_sync_progress(progress)
        # Save GameCredits usd price
        price = analizer.get_game_price()
        analizer.save_game_price(price)

class FiveMinuteTask(Task):
    """
    Checks for new information from Coinmarketcap about GameCredits
    on every 5 minutes, because Coinmarketcap api refreshes every
    5 minutes, and inserts it to database
    """
    @only_one(key="FiveMinuteTask", timeout=config.getint('syncer', 'task_lock_timeout'))
    def run(self, **kwargs):
        client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))
        database = MongoDatabaseGateway(client.exploder, config)
        coinmarketcap_analyzer = CoinmarketcapAnalyzer(database, config)

        # Information from CoinMarketCap
        coinmarketcap_info = coinmarketcap_analyzer.get_coinmarketcap_game_info()

        # Our time that we are inserting our price, this has to be int because of the time calculations
        price_timestamp = int(time.time())

        # Method that saves price info and timestamp
        coinmarketcap_analyzer.save_price_history(
            coinmarketcap_info['price_usd'],
            coinmarketcap_info['price_btc'],
            coinmarketcap_info['market_cap_usd'],
            price_timestamp
        )

        # Gets GAME old price, 24h ago
        old_price = coinmarketcap_analyzer.get_old_btc_price(price_timestamp)
        # If we have information about the price 24h ago
        if old_price:
            try:
                old_price = Decimal(max(old_price))
                # Round old_price number by 8 decimals
                old_price = round(Decimal(old_price), 8)

                new_price = Decimal(coinmarketcap_info['price_btc'])
                # Round new_price number by 8 decimals
                new_price = round(Decimal(new_price), 8)
                
                percent_change_24h_btc = coinmarketcap_analyzer.btc_price_difference_percentage(old_price, new_price)

                database.update_price_stats(
                    float(coinmarketcap_info['price_usd']),
                    float(coinmarketcap_info['price_btc']),
                    float(coinmarketcap_info['percent_change_24h_usd']),
                    float(percent_change_24h_btc),
                    float(coinmarketcap_info['24h_volume_usd'])
                )
            except InvalidOperation as e:
                logging.error('FIVE_MINUTE_TASK_FAILED ERROR: %s' %e)

app = SyncerCelery('tasks', broker='redis://localhost:6379/0')
app.conf.result_backend = 'redis://localhost:6379/0'
app.tasks.register(SyncTask)
app.tasks.register(DailyTask)
app.tasks.register(HalfMinuteTask)
app.tasks.register(FiveMinuteTask)

app.conf.beat_schedule = {
    'sync-every-10-seconds': {
        'task': 'syncer.tasks.SyncTask',
        'schedule': 10.0,
    },
    'hashrate-once-a-day': {
        'task': 'syncer.tasks.DailyTask',
        'schedule': crontab(minute=0, hour=12),  # It's high noon
    },
    'every-30-seconds': {
        'task': 'syncer.tasks.HalfMinuteTask',
        'schedule': 30.0,
    },
    'info-every-5-minutes': {
        'task': 'syncer.tasks.FiveMinuteTask',
        'schedule': crontab(minute='*/5'),
    },
}

app.conf.timezone = 'UTC'
