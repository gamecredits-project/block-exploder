import pymongo

from factories import BlockFactory, VoutFactory, TransactionFactory
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer


class DatabaseGateway(object):
    @property
    def highest_block(self):
        """
        Return the highest known block in the DB
        """
        mongo_block = self.blocks.find_one(sort=[("height", -1)])

        if mongo_block:
            return BlockFactory.from_mongo(mongo_block)
        else:
            return None

    @highest_block.setter
    def highest_block(self, value):
        pass

    def __init__(self, database, cache_size=1000):
        self.cache_size = cache_size

        # Mongo collections to persist the blockchain
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vins = database.vin
        self.vouts = database.vout

        # Caches for batch writing
        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

        # When ran the first time create the indexes
        if not self.highest_block:
            self._create_indexes()

    def _create_indexes(self):
        self.blocks.create_index([("height", pymongo.DESCENDING)])
        self.blocks.create_index([("hash", pymongo.HASHED)])

    def flush_cache(self):
        if self.block_cache:
            self.blocks.insert_many(self.block_cache.values())

        if self.tr_cache:
            self.transactions.insert_many(self.tr_cache)

        if self.vin_cache:
            self.vins.insert_many(self.vin_cache)

        if self.vout_cache:
            self.vouts.insert_many(self.vout_cache)

        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

    def put_block(self, block):
        if block.hash in self.block_cache:
            raise KeyError("[put_block] Block with hash %s already exists in the database" % block.hash)

        # Write the block to cache
        self.block_cache[block.hash] = BlockSerializer.to_database(block)

        if len(self.block_cache) >= self.cache_size:
            self.flush_cache()

    def get_block(self, block_hash, no_cache=False):
        """
        Tries to find it in cache and if it misses finds it in the DB
        """
        found = None
        if not no_cache and block_hash in self.block_cache:
            found = self.block_cache[block_hash]
        else:
            found = self.blocks.find_one({"hash": block_hash})

        if not found:
            raise KeyError("[get_block_FAILED] Block with hash %s not found." % block_hash)

        return BlockFactory.from_mongo(found)

    def get_latest_blocks(self, limit=10, offset=0):
        return [BlockFactory.from_mongo(block) for block in self.blocks.find(sort=[("height", -1)])
                .skip(offset).limit(limit)]

    def delete_block(self, block_hash):
        if block_hash in self.block_cache:
            del self.block_cache[block_hash]
        else:
            self.block_db.delete_one({"hash": block_hash})

    def update_block(self, block_hash, update_dict):
        if block_hash in self.block_cache:
            for (key, val) in update_dict.iteritems():
                self.block_cache[block_hash][key] = val
        else:
            self.blocks.update_one({
                'hash': block_hash
            }, {
                '$set': update_dict
            })

    def put_transactions(self, tx, flush=False):
        # Persist trs, vins and outs
        for tr in tx:
            self.tr_cache.append(TransactionSerializer.to_database(tr))

            for vin in tr.vin:
                self.vin_cache.append(VinSerializer.to_database(vin))

            for vout in tr.vout:
                self.vout_cache += VoutSerializer.to_database(vout)

        if flush:
            self.flush_cache()

    def get_transaction(self, txid):
        transaction = self.transactions.find_one({"txid": txid})

        if not transaction:
            raise KeyError("No transaction with that txid in the database")

        return TransactionFactory.from_mongo(transaction)

    def get_block_transactions(self, blockhash):
        transactions = self.transactions.find({"blockhash": blockhash})
        return [TransactionFactory.from_mongo(tr) for tr in transactions]

    def get_address_transactions(self, address):
        vouts = self.vouts.find({"address": address})
        transactions = []
        for v in vouts:
            transactions.append(self.get_transaction(v['txid']))

        return transactions

    def get_unspent_for_address(self, address):
        outs = self.vouts.find({"address": address})

        if not outs:
            raise KeyError("No outputs to that address")

        unspent = []
        for out in outs:
            spend = self.vins.find_one({"prev_txid": out['txid'], "vout_index": out['index']})

            if not spend:
                unspent.append(out)

        return [VoutFactory.from_mongo(out) for out in unspent]
