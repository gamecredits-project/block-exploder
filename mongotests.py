from pymongo import MongoClient

client = MongoClient()

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