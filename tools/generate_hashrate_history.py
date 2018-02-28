import os
import ConfigParser
import time
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy

from syncer.interactors import BlockchainAnalyzer
from syncer.gateways import MongoDatabaseGateway


CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)


def generate_hashrate_history(now, days=30):
    client = MongoClient()
    database = MongoDatabaseGateway(client.exploder, config)
    rpc_client = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                  % (config.get('syncer', 'rpc_user'), config.get('syncer', 'rpc_password')))

    analizer = BlockchainAnalyzer(database, rpc_client, config)
    seconds_in_day = 86400
    for x in xrange(days):
        hash_rate = analizer.get_network_hash_rate(end_time=now)
        analizer.save_network_hash_rate(hash_rate=hash_rate, timestamp=now)
        now -= seconds_in_day
        print "hash_rate: %r, timestamp: %r" % (hash_rate, now)


if __name__ == "__main__":
    generate_hashrate_history(now=time.time())
