from pymongo import MongoClient
import os
import ConfigParser

CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

client = MongoClient('mongodb://%s:%s@127.0.0.1/exploder' %(config.get('syncer', 'mongo_user'), config.get('syncer', 'mongo_pass')))

db = client.exploder

# db.blocks.aggregate(
#     {"$group" : { "_id": "$blockhash", "count": { "$sum": 1 } } },
#     {"$match": {"_id" :{ "$ne" : null } , "count" : {"$gt": 1} } }, 
#     {"$project": {"blockhash" : "$_id", "_id" : 0} }
# )

# There should be no duplicate blockhashes
pipeline = [
    {"$group": {"_id": "$blockhash", "count": {"$sum": 1}}},
    {"$match": {"_id" :{ "$ne" : None } , "count" : {"$gt": 1} } },
    {"$project": {"blockhash": "$_id", "_id": 0}}
]

assert len(list(db.blocks.aggregate(pipeline))) == 0

# There should be no duplicate txids
pipeline = [
    {"$group": {"_id": "$txid", "count": {"$sum": 1}}},
    {"$match": {"_id" :{ "$ne" : None } , "count" : {"$gt": 1} } },
    {"$project": {"blockhash": "$_id", "_id": 0}}
]