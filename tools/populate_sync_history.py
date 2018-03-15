from pymongo import MongoClient

from syncer.serializers import SyncHistorySerializer
import os
import ConfigParser

CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

def populate_sync_history():
    client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))
    db = client.exploder
    db.sync_history.insert_many(
        [
            SyncHistorySerializer.to_database(1496232349, 1496983245, 15, 328190),
            SyncHistorySerializer.to_database(1496552132, 1496602132, 328191, 948122),
            SyncHistorySerializer.to_database(1496646127, 1496648329, 948123, 1217383),
            SyncHistorySerializer.to_database(1496661111, 1496661519, 1217384, 1685078)
        ]
    )
    print "Done"


if __name__ == "__main__":
    populate_sync_history()
