import os
from factories import BlockFactory
from helpers import has_length, is_block_file, calculate_target, calculate_work
from bitcoinrpc.authproxy import AuthServiceProxy
import pymongo
import pdb

MAIN_CHAIN = 0
PERSIST_EVERY = 1000  # blocks
RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"
RPC_SYNC_PERCENT = 97


class Blockchain(object):
    @property
    def highest_block(self):
        mongo_block = self.block_db.find_one(sort=[("height", -1)])

        if mongo_block:
            return BlockFactory.from_mongo(mongo_block)
        else:
            return None

    def __init__(self, database, blocks_dir):
        # Num of forks encountered while building the tree
        self.num_forks = 0

        # Num of reconvergences done while building the tree
        self.num_convergences = 0

        # Databases to persist the blockchain
        self.block_db = database.blocks
        self.tr_db = database.transactions
        self.vin_db = database.vin
        self.vout_db = database.vout

        # Caches for batch writing
        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

        # On init previous block is the highest known block
        self.previous_block = self.highest_block

        # When ran the first time create the indexes
        if not self.previous_block:
            self._create_indexes()

        self.first_iter = True

        if os.path.isdir(blocks_dir):
            self.blk_files = sorted(
                [os.path.join(blocks_dir, f) for f in os.listdir(blocks_dir) if is_block_file(f)]
            )
        else:
            raise Exception("Given path is not a directory")

        self.rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                    % (RPC_USER, RPC_PASSWORD))

    def _create_indexes(self):
        self.block_db.create_index([("height", pymongo.DESCENDING)])
        self.block_db.create_index([("hash", pymongo.HASHED)])

    def sync(self, limit=0):
        client_height = self.rpc.getblockcount()
        highest_known = self.highest_block
        progress = float(highest_known.height * 100) / client_height

        if progress < RPC_SYNC_PERCENT:
            self._sync_stream(highest_known, client_height, limit)

        self._sync_rpc(client_height, limit)

    def _sync_stream(self, highest_known, client_height, limit):
        print "[SYNC_STREAM] Started sync from .dat files"
        parsed = 0

        # Seek to last parsed block file
        if highest_known:
            self.blk_files = self.blk_files[highest_known.dat["index"]:]
            progress = float(highest_known.height * 100) / client_height
        else:
            progress = 0

        for (i, f) in enumerate(self.blk_files):
            stream = open(f, 'r')

            # Seek to the end of the last parsed block
            # in the first iteration
            if i == 0 and highest_known:
                stream.seek(highest_known.dat['end'])

            while progress < RPC_SYNC_PERCENT and has_length(stream, 80) and (limit == 0 or parsed < limit):
                res = BlockFactory.from_stream(stream)
                block = self.add_block(res['block'])
                # print block
                parsed += 1
                self.persist_transactions(res['transactions'])

                progress = float(block.height * 100) / client_height

                if block.height % 1000 == 0:
                    print "Progress: %s%%" % progress

            self.flush_cache()

    def _sync_rpc(self, client_height, limit):
        print "[SYNC_RPC] Started sync from rpc"
        parsed = 0

        # Compare our highest known block to it's repr in RPC
        # if they have the same height and previousblockhash there was no reconverge
        # and we can just insert the blocks sequentially by following the nextblockhash links
        our_block = self.highest_block
        rpc_block = BlockFactory.from_rpc(self.rpc.getblock(our_block.hash))

        if our_block.height == rpc_block.height and our_block.previousblockhash == rpc_block.previousblockhash:
            while rpc_block.nextblockhash and parsed < limit:
                rpc_block = BlockFactory.from_rpc(self.rpc.getblock(our_block.hash))
                # pdb.set_trace()
                rpc_block.chain = MAIN_CHAIN
                rpc_block.target = calculate_target(rpc_block.bits)
                rpc_block.work = calculate_work(rpc_block.target)
                rpc_block.difficulty = float(rpc_block.difficulty)
                self.block_db.insert_one(rpc_block.to_mongo())
                parsed += 1
        else:
            # Else find the reconverge point by going backwards and finding the first block
            # that is the same in our db and rpc and then sync upwards from there
            raise Exception("[SYNC_RPC] Reconverge")

    def add_block_from_rpc(self, block):
        highest_block = self.highest_known

        if not highest_block:
            raise Exception("[SYNC_RPC] Previous block is None")

        if block.previousblockhash == highest_block.hash:
            block.chain = MAIN_CHAIN
            block.work = calculate_work(block)
            block.target = calculate_target(block)
            self.update_block(block.previousblockhash, {"nextblockhash": block.hash})
            self.persist_block(block, flush=True)

    def add_block(self, block):
        # If the previous_block is None the db is empty
        if not self.previous_block:
            block.height = 0
            block.chainwork = block.work
            block.chain = MAIN_CHAIN
            self.previous_block = block
            self.first_iter = False
            return block

        if block.previousblockhash == self.previous_block.hash:
            # Update the previous block nextblockhash and persist it to the db
            self.previous_block.nextblockhash = block.hash

            if not self.first_iter:
                self.persist_block(self.previous_block)

            block.height = self.previous_block.height + 1
            block.chainwork = self.previous_block.chainwork + block.work
            block.chain = MAIN_CHAIN
            self.previous_block = block
        else:
            fork_point = self.find_block(block.previousblockhash)

            if fork_point.chain == MAIN_CHAIN:
                print "[FORK] Fork on block %s" % block.previousblockhash
                self.num_forks += 1
                block.height = fork_point.height + 1
                block.chainwork = fork_point.chainwork + block.work
                block.chain = self.num_forks
            else:
                print "[FORK_GROW] A sidechain is growing."
                block.height = fork_point.height + 1
                block.chainwork = fork_point.chainwork + block.work
                block.chain = self.num_fork
                self.update_block(block.previousblockhash, {"nextblockhash": block.hash})

            if block.chainwork > self.previous_block.chainwork:
                print "[RECONVERGE] Reconverge, new top is now %s" % block.hash
                self.previous_block = block
                self.num_convergences += 1
                self.reconverge(block)
            else:
                if not self.first_iter:
                    self.persist_block(block)

        self.first_iter = False
        return block

    def reconverge(self, new_top_block):
        current = self.find_block(new_top_block.hash)

        # Traverse up to the fork point and mark all nodes in sidechain as
        # part of main chain
        while current['chain'] != MAIN_CHAIN:
            self.update_block(current['hash'], {"chain": MAIN_CHAIN})
            parent = self.find_block(current['previousblockhash'])

            if parent['chain'] == MAIN_CHAIN:
                first_in_sidechain_hash = current['hash']

            current = parent

        # Save tne fork points hash
        fork_point_hash = current['hash']

        # Traverse down the fork point and mark all main chain nodes part
        # of the sidechain
        while current['nextblockhash'] is not None:
            next_block = self.find_block(current['nextblockhash'])
            self.update_block(next_block['hash'], {"chain": self.num_forks + 1})
            current = next_block

        self.update_block(fork_point_hash, {"nextblockhash": first_in_sidechain_hash})

    def persist_block(self, block):
        # Write the block to cache
        self.block_cache[block.hash] = block.to_mongo()

        if len(self.block_cache) >= PERSIST_EVERY:
            # Flush cache to db
            self.flush_cache()

    def persist_transactions(self, tx, flush=False):
        # Persist trs, vins and outs
        for tr in tx:
            self.tr_cache.append(tr.to_mongo())

            for vin in tr.vin:
                self.vin_cache.append(vin.to_mongo(tr.txid))

            for (i, vout) in enumerate(tr.vout):
                self.vout_cache += vout.to_mongo(tr.txid, i)

        if flush:
            self.flush_cache()

    def flush_cache(self):
        if self.block_cache:
            self.block_db.insert_many(self.block_cache.values())

        if self.tr_cache:
            self.tr_db.insert_many(self.tr_cache)

        if self.vin_cache:
            self.vin_db.insert_many(self.vin_cache)

        if self.vout_cache:
            self.vout_db.insert_many(self.vout_cache)

        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

    def find_block(self, block_hash):
        """
        Tries to find it in cache and if it misses finds it in the DB
        """
        found = None
        if block_hash in self.block_cache:
            found = self.block_cache[block_hash]
        else:
            found = self.block_db.find_one({"hash": block_hash})

        if not found:
            raise Exception("[FIND_BLOCK_FAILED] Block with hash %s not found." % block_hash)

        return BlockFactory.from_mongo(found)

    def update_block(self, block_hash, update_dict):
        if block_hash in self.block_cache:
            for (key, val) in update_dict.iteritems():
                self.block_cache[block_hash][key] = val
        else:
            self.block_db.update_one({
                'hash': block_hash
            }, {
                '$set': update_dict
            })

