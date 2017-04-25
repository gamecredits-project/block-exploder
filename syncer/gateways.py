import pymongo

from factories import MongoBlockFactory, MongoTransactionFactory, MongoVoutFactory, MongoVinFactory
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer
from pymongo import MongoClient


def get_mongo_connection():
    return MongoClient()


class MongoDatabaseGateway(object):
    def __init__(self, database, cache=True, cache_size=1000):
        self.cache_size = cache_size

        # Mongo collections to persist the blockchain
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vins = database.vin
        self.vouts = database.vout

        # Cache mode enabled?
        self.cache = cache

        # Caches for batch writing
        self.block_cache = {}
        self.tr_cache = {}
        self.vin_cache = []
        self.vout_cache = []

        # When ran the first time create the indexes
        if not self.get_highest_block():
            self.create_indexes()

    #####################
    #  UTILITY METHODS  #
    #####################
    def create_indexes(self):
        self.blocks.create_index([("height", pymongo.DESCENDING)])
        self.blocks.create_index([("hash", pymongo.HASHED)])

    def flush_cache(self):
        if self.block_cache:
            self.blocks.insert_many(self.block_cache.values())

        if self.tr_cache:
            self.transactions.insert_many(self.tr_cache.values())

        if self.vin_cache:
            self.vins.insert_many(self.vin_cache)

        if self.vout_cache:
            self.vouts.insert_many(self.vout_cache)

        self.block_cache = {}
        self.tr_cache = {}
        self.vin_cache = []
        self.vout_cache = []

    ###################
    #  BLOCK METHODS  #
    ###################
    def get_highest_block(self):
        """
        Return the highest known block in the DB
        """
        mongo_block = self.blocks.find_one(sort=[("height", -1)])

        if mongo_block:
            return MongoBlockFactory.from_mongo(mongo_block)
        else:
            return None

    def get_block_by_hash(self, block_hash):
        """
        Tries to find it in cache and if it misses finds it in the DB
        """
        found = None
        if self.cache and block_hash in self.block_cache:
            found = self.block_cache[block_hash]

        if not self.cache or not found:
            found = self.blocks.find_one({"hash": block_hash})

        if not found:
            raise KeyError("[get_block_by_hash] Block with hash %s not found." % block_hash)

        return MongoBlockFactory.from_mongo(found)

    def get_block_by_height(self, block_height):
        found = None
        if self.cache:
            for (blockhash, block) in self.block_cache.iteritems():
                if block['height'] == block_height:
                    found = block

        if not self.cache or not found:
            found = self.blocks.find_one({"height": block_height})

        if not found:
            raise KeyError("[get_block_by_height] Block with height %s not found." % block_height)

        return MongoBlockFactory.from_mongo(found)

    def get_latest_blocks(self, limit=10, offset=0):
        return [MongoBlockFactory.from_mongo(block) for block in self.blocks.find(sort=[("height", -1)])
                .skip(offset).limit(limit)]

    def put_block(self, block):
        if block.hash in self.block_cache:
            raise KeyError("[put_block] Block with hash %s already exists in the database" % block.hash)

        if self.cache:
            # Write the block to cache
            self.block_cache[block.hash] = BlockSerializer.to_database(block)

            if len(self.block_cache) >= self.cache_size:
                self.flush_cache()
        else:
            self.blocks.insert_one(BlockSerializer.to_database(block))

    def delete_block(self, block_hash):
        if self.cache and block_hash in self.block_cache:
            del self.block_cache[block_hash]
        else:
            self.blocks.delete_one({"hash": block_hash})

    def update_block(self, block_hash, update_dict):
        if self.cache and block_hash in self.block_cache:
            for (key, val) in update_dict.iteritems():
                self.block_cache[block_hash][key] = val
        else:
            self.blocks.update_one({
                'hash': block_hash
            }, {
                '$set': update_dict
            })

    #########################
    #  TRANSACTION METHODS  #
    #########################
    def get_transaction_by_txid(self, txid):
        if self.cache and txid in self.tr_cache:
            return MongoTransactionFactory.from_mongo(self.tr_cache[txid])

        transaction = self.transactions.find_one({"txid": txid})

        if not transaction:
            raise KeyError("No transaction with that txid in the database")

        return MongoTransactionFactory.from_mongo(transaction)

    def get_transactions_by_blockhash(self, blockhash):
        transactions = self.transactions.find({"blockhash": blockhash})
        return [MongoTransactionFactory.from_mongo(tr) for tr in transactions]

    def get_transactions_by_address(self, address):
        vouts = self.vouts.find({"address": address})
        transactions = []
        for v in vouts:
            transactions.append(self.get_transaction_by_txid(v['txid']))

        return transactions

    def put_transaction(self, tr):
        if self.cache:
            self.tr_cache[tr.txid] = (TransactionSerializer.to_database(tr))

            for vin in tr.vin:
                self.vin_cache.append(VinSerializer.to_database(vin, tr.txid))

            for (index, vout) in enumerate(tr.vout):
                self.vout_cache += VoutSerializer.to_database(vout, tr.txid, index)
        else:
            vins = []
            vouts = []
            for vin in tr.vin:
                vins.append(VinSerializer.to_database(vin, tr.txid))

            for vout in tr.vout:
                vouts += VoutSerializer.to_database(vout, tr.txid, tr.index)

            self.transactions.insert_one(TransactionSerializer.to_database(tr))
            self.vin.insert_many(vins)
            self.vout.insert_many(vouts)

    ########################
    #  INPUTS AND OUTPUTS  #
    ########################
    def get_vouts_by_address(self, address):
        return [MongoVoutFactory.from_mongo(vout) for vout in self.vouts.find({"address": address})]

    def get_vin_by_vout(self, vout):
        if self.cache:
            found = [
                vin for vin in self.vin_cache if vin['prev_txid'] == vout.txid and vin['vout_index'] == vout.index
            ]
            if found:
                return MongoVinFactory.from_mongo(found[0])

        found = self.vins.find_one({"prev_txid": vout.txid, "vout_index": vout.index})

        if not found:
            raise KeyError("[get_vin_by_vout] Input with prev_txid=%s and vout_index=%s doesn't exist"
                           % (vout.txid, vout.index))

        return found

    def put_vin(self, vin, txid):
        if self.cache:
            self.vin_cache.append(VinSerializer.to_database(vin, txid))
        else:
            self.vins.insert_one(VinSerializer.to_database(vin, txid))

    def get_unspent_vouts_for_address(self, address):
        outs = self.get_vouts_by_address(address)

        if not outs:
            raise KeyError("No outputs to that address")

        unspent = [o for o in outs if not self.get_vin_by_vout(o)]
        return [MongoVoutFactory.from_mongo(out) for out in unspent]
