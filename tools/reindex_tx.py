from syncer.gateways import MongoDatabaseGateway
import os
import ConfigParser
from pymongo import MongoClient


CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

mongo = MongoClient()


# Fork point -> 
db = MongoDatabaseGateway(database=mongo.exploder, config=config)

fork_point = 1981542

def remove_after_fork():
    blocks_arr = db.blocks.find({ 'height': { '$gte': fork_point }})
        
    for blocks in blocks_arr:
        db.blocks.remove({ 'height': blocks['height'] })

        for tx in blocks['tx']:
            print 'Deleted -> %s' %blocks['height']
            db.transactions.remove({ 'txid': tx})
    print 'I am done Master!'

def reindex_transactions():
    blocks_arr = db.blocks.find({ 'height': { '$lt': fork_point }})
    
    for blocks in blocks_arr:
        
        for tx in blocks['tx']:
            if blocks['chain'] == 'main_chain':
                print 'MainChain -> %s' %blocks['height']
                db.transactions.update({ 'txid': tx}, { '$set': {'main_chain': True}})
            else:
                print 'SideChain -> %s' %blocks['height']
                db.transactions.update({ 'txid': tx}, { '$set': {'main_chain': False}})
    
    print 'I am done Master!'


reindex_transactions()
# remove_after_fork()