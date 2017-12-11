import pymongo
from decimal import Decimal
import time

from factories import MongoBlockFactory, MongoTransactionFactory
from serializers import BlockSerializer, TransactionSerializer, \
    HashrateSerializer, SyncHistorySerializer, NetworkStatsSerializer, \
    ClientInfoSerializer, ClientSyncProgressSerializer, PriceSerializer,\
    PriceHistorySerializer, PriceStatsSerializer
from pymongo import MongoClient


MAIN_CHAIN = 'main_chain'


def get_mongo_connection():
    return MongoClient()


class MongoDatabaseGateway(object):
    def __init__(self, database, config):
        # Mongo collections to persist the blockchain
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.hashrate = database.hashrate
        self.network_stats = database.network_stats
        self.sync_history = database.sync_history
        self.client_info = database.client_info
        self.price_history = database.price_history
        self.price_stats = database.price_stats

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
        self.blocks.create_index([("chain", pymongo.ASCENDING)])
        self.transactions.create_index([("txid", pymongo.HASHED)])
        self.transactions.create_index([("blockhash", pymongo.ASCENDING)])
        self.transactions.create_index([("blocktime", pymongo.DESCENDING)])
        self.transactions.create_index([("vout.addresses", pymongo.DESCENDING)])
        self.transactions.create_index([("vin.prev_txid", pymongo.DESCENDING)])

    def flush_cache(self):
        if self.block_cache:
            self.blocks.insert_many(
                [BlockSerializer.to_database(block) for block in self.block_cache.values()])

        if self.tr_cache:
            self.transactions.insert_many(
                [TransactionSerializer.to_database(tr) for tr in self.tr_cache.values()])

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

    def get_blockchain_height(self):
        highest_block = self.get_highest_block()

        if not highest_block:
            return 0

        return highest_block.height

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

    def get_blocks_between_time(self, start, end):
        return self.blocks.find({"time": {"$gt": start, "$lt": end}})

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
        transactions = self.transactions.find({"vout.addresses": address})

        return [MongoTransactionFactory.from_mongo(tr) for tr in transactions]

    def put_transaction(self, tr):
        if tr.txid in self.tr_cache:
            raise KeyError("[put_transaction] Transaction with txid %s already exists in the database" % tr.txid)

        self.tr_cache[tr.txid] = tr

    def mark_output_spent(self, txid, vout_index):
        if txid in self.tr_cache:
            self.tr_cache[txid].vout[vout_index].spent = True
        else:
            self.transactions.update_one({
                'txid': txid
            }, {
                '$set': {"vout.%s.spent" % vout_index: True}
            })

    #########################
    #   NETWORK METHODS    #
    #########################
    def put_hashrate(self, hash_rate, timestamp):
        if hash_rate and timestamp:
            self.hashrate.insert_one(HashrateSerializer.to_database(hash_rate, timestamp))

    def update_network_stats(self, supply, blockchain_size):
        stats = self.network_stats.find_one()

        if stats is None:
            self.network_stats.insert_one(NetworkStatsSerializer.to_database(supply, blockchain_size))
        else:
            self.network_stats.update_one(
                {'_id': stats['_id']}, {"$set": NetworkStatsSerializer.to_database(supply, blockchain_size)}
            )

    def update_game_price(self, price):
        stats = self.network_stats.find_one()

        if stats is None:
            self.network_stats.insert_one(PriceSerializer.to_database(price))
        else:
            self.network_stats.update_one(
                {'_id': stats['_id']}, {"$set": PriceSerializer.to_database(price)}
            )

    def put_sync_history(self, start_time, end_time, start_block_height, end_block_height):
        self.sync_history.insert_one(
            SyncHistorySerializer.to_database(start_time, end_time, start_block_height, end_block_height)
        )

    def put_price_history_info(self, price_usd, price_btc, market_cap_usd, timestamp):
        self.price_history.insert_one(
            PriceHistorySerializer.to_database(price_usd, price_btc, market_cap_usd, timestamp)
        )

    def get_old_btc_price(self, timestamp):
        # old timestamp is 10 minutes older than the new one
        # old_timestamp = timestamp - 600
        # old_timestamp is 1h older than the new one
        old_timestamp = timestamp - 3600
        result = self.price_history.find({
            'timestamp': {'$gte': old_timestamp - 240, '$lte': old_timestamp + 240}
            # 'timestamp': {'$gte': old_timestamp - 60, '$lte': old_timestamp + 60}
        })

        all_res = []
        for res in result:
            all_res.append(res)

        return all_res

    def update_price_stats(self, percentChange24hUSD, percentChange24hBTC, volume24hUSD):
        stats = self.price_stats.find_one()

        if stats is None:
            self.price_stats.insert_one(
                PriceStatsSerializer.to_database(
                    percentChange24hUSD, percentChange24hBTC,
                    volume24hUSD, int(time.time())))
        else:
            self.price_stats.update_one(
                {'_id': stats['_id']},
                {"$set": PriceStatsSerializer.to_database(
                    percentChange24hUSD, percentChange24hBTC,
                    volume24hUSD, int(time.time()))
                }
            )

    #########################
    #    CLIENT METHODS     #
    #########################
    def put_client_info(self, version, ip, peer_info):
        client_info = self.client_info.find_one()

        for peer in peer_info:
            for key, value in peer.iteritems():
                if isinstance(value, Decimal):
                    peer[key] = str(value)

        if client_info is None:
            self.client_info.insert_one(ClientInfoSerializer.to_database(version, ip, peer_info))
        else:
            self.client_info.update_one(
                {'_id': client_info['_id']}, {"$set": ClientInfoSerializer.to_database(version, ip, peer_info)}
            )

    def update_sync_progress(self, progress):
        client_info = self.client_info.find_one()

        if client_info is None:
            self.client_info.insert_one(ClientSyncProgressSerializer.to_database(progress))
        else:
            self.client_info.update_one(
                {'_id': client_info['_id']}, {"$set": ClientSyncProgressSerializer.to_database(progress)}
            )
