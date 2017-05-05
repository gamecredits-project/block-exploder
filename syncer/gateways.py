import pymongo

from factories import MongoBlockFactory, MongoTransactionFactory, MongoVoutFactory, MongoVinFactory
from serializers import BlockSerializer, TransactionSerializer, VinSerializer, VoutSerializer
from pymongo import MongoClient


MAIN_CHAIN = 'main_chain'


def get_mongo_connection():
    return MongoClient()


class MongoDatabaseGateway(object):
    def __init__(self, database, config):
        # Mongo collections to persist the blockchain
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vins = database.vin
        self.vouts = database.vout

        self.cache_size = config.getint('syncer', 'cache_size')

        # Caches for batch writing
        self.block_cache = {}
        self.tr_cache = {}

        self._highest_block = None

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
            self.blocks.insert_many([BlockSerializer.to_database(block) for block in self.block_cache.values()])

        if self.tr_cache:
            self.transactions.insert_many([TransactionSerializer.to_database(tr) for tr in self.tr_cache.values()])

        vins_to_insert = []
        vouts_to_insert = []
        for tr in self.tr_cache.values():
            vins_to_insert += [VinSerializer.to_database(vin, tr.txid) for vin in tr.vin]
            for (index, vout) in enumerate(tr.vout):
                vouts_to_insert += VoutSerializer.to_database(vout, tr.txid, index)

        self.vins.insert_many(vins_to_insert)
        self.vouts.insert_many(vouts_to_insert)
        self.block_cache = {}
        self.tr_cache = {}

    def get_chain_identifiers(self):
        return self.blocks.distinct("chain")

    ###################
    #  BLOCK METHODS  #
    ###################
    def get_highest_block(self):
        """
        Return the highest known block in the main chain
        """
        if self._highest_block is not None:
            return self._highest_block

        highest_in_cache = None
        if self.block_cache:
            main_chain = [block for block in self.block_cache.values() if block.chain == MAIN_CHAIN]
            if main_chain:
                highest_in_cache = max(main_chain, key=lambda b: b.height)

        highest_in_db = self.blocks.find_one({"chain": MAIN_CHAIN}, sort=[("height", -1)])
        if highest_in_db:
            mongo_block_transactions = self.transactions.find({"blockhash": highest_in_db['hash']})
            highest_in_db = MongoBlockFactory.from_mongo(highest_in_db, mongo_block_transactions)

        highest_block = max([highest_in_cache, highest_in_db])
        self.set_highest_block(highest_block)
        return self._highest_block

    def set_highest_block(self, block):
        self._highest_block = block

    def get_block_by_hash(self, block_hash):
        """
        Tries to find it in cache and if it misses finds it in the DB
        """
        if block_hash in self.block_cache:
            return self.block_cache[block_hash]

        mongo_block = self.blocks.find_one({"hash": block_hash})

        if not mongo_block:
            raise KeyError("[get_block_by_hash] Block with hash %s not found." % block_hash)

        mongo_block_transactions = self.transactions.find({"blockhash": mongo_block['hash']})
        return MongoBlockFactory.from_mongo(mongo_block, mongo_block_transactions)

    def get_block_by_height(self, block_height):
        found = [block for block in self.block_cache.values() if block.height == block_height]
        if found:
            return found[0]

        mongo_block = self.blocks.find_one({"height": block_height})

        if mongo_block:
            mongo_block_transactions = self.transactions.find({"blockhash": mongo_block['hash']})
            found = MongoBlockFactory.from_mongo(mongo_block, mongo_block_transactions)

        if not found:
            raise KeyError("[get_block_by_height] Block with height %s not found." % block_height)

        return found

    def get_blocks_by_chain(self, chain):
        in_cache = [block for block in self.block_cache.values() if block.chain == chain]

        in_db = []
        mongo_blocks = self.blocks.find({"chain": chain})
        for mongo_block in mongo_blocks:
            mongo_block_transactions = self.transactions.find({"blockhash": mongo_block['hash']})
            in_db.append(MongoBlockFactory.from_mongo(mongo_block, mongo_block_transactions))

        return in_cache + in_db

    def get_blocks_higher_than(self, height):
        """
        Returns blocks in the MAIN_CHAIN with block.height > height
        """
        cache_blocks = sorted([block for block in self.block_cache.values() if block.chain == MAIN_CHAIN],
                              key=lambda b: b.height)

        if cache_blocks and cache_blocks[0].height < height:
            result = [block for block in cache_blocks if block.height > height]
        else:
            mongo_blocks = self.blocks.find({"height": {"$gt": height}, "chain": MAIN_CHAIN})
            result = [
                MongoBlockFactory.from_mongo(block, self.transactions.find({"blockhash": block['hash']}))
                for block in mongo_blocks
            ]

            result += cache_blocks

        return result

    def put_block(self, block):
        if block.hash in self.block_cache:
            raise KeyError("[put_block] Block with hash %s already exists in the database" % block.hash)

        # Write the block to cache
        self.block_cache[block.hash] = block

        for tr in block.tx:
            self.tr_cache[tr.txid] = tr

        if len(self.block_cache) >= self.cache_size:
            self.flush_cache()

        if self._highest_block and block.chain == MAIN_CHAIN and self._highest_block.height < block.height:
            self.set_highest_block(block)

    def delete_block(self, block_hash):
        if block_hash in self.block_cache:
            del self.block_cache[block_hash]
        else:
            self.blocks.delete_one({"hash": block_hash})

        if self._highest_block and block_hash == self._highest_block.hash:
            self._highest_block = None

    def update_block(self, block_hash, update_dict):
        if block_hash in self.block_cache:
            for (key, val) in update_dict.iteritems():
                setattr(self.block_cache[block_hash], key, val)
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
        if txid in self.tr_cache:
            return self.tr_cache[txid]

        transaction = MongoTransactionFactory.from_mongo(self.transactions.find_one({"txid": txid}))

        if not transaction:
            raise KeyError("No transaction with that txid in the database")

        return transaction

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
        if tr.txid in self.tr_cache:
            raise KeyError("[put_transaction] Transaction with txid %s already exists in the database" % tr.txid)

        self.tr_cache[tr.txid] = tr

