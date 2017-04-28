import os
from gamecredits.helpers import has_length, is_block_file
import datetime
import itertools
from gamecredits.factories import BlockFactory

MAIN_CHAIN = "main_chain"
PERSIST_EVERY = 1000  # blocks
RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"
STREAM_SYNC_LIMIT_DEFAULT = 99
MIN_STREAM_THRESH = 1500000


class Blockchain(object):
    def __init__(self, database):
        # Instance of MongoDatabaseGateway
        self.db = database

        # Global counter for creating unique identifiers
        self._counter = itertools.count()
        # Skip the taken identifiers
        while self._get_unique_chain_identifier() in self.db.get_chain_identifiers():
            pass

    def _get_unique_chain_identifier(self):
        return "chain%s" % next(self._counter)

    def _create_coinbase(self, block):
        block.height = 0
        block.chainwork = block.work
        block.chain = MAIN_CHAIN
        self.db.put_block(block)
        return block

    def _append_to_main_chain(self, block):
        chain_peak = self.db.get_block_by_hash(block.previousblockhash)

        block.height = chain_peak.height + 1
        block.chainwork = chain_peak.chainwork + block.work
        block.chain = MAIN_CHAIN

        self.db.put_block(block)
        self.db.update_block(chain_peak.hash, {"nextblockhash": block.hash})
        return block

    def _create_fork_of_main_chain(self, block, fork_point):
        print "[FORK] Fork on block %s" % block.previousblockhash
        block.height = fork_point.height + 1
        block.chainwork = fork_point.chainwork + block.work
        block.chain = self._get_unique_chain_identifier()
        self.db.put_block(block)
        return block

    def _grow_sidechain(self, block, fork_point):
        print "[FORK_GROW] A sidechain is growing."
        block.height = fork_point.height + 1
        block.chainwork = fork_point.chainwork + block.work
        block.chain = fork_point.chain
        self.db.put_block(block)
        self.db.update_block(block.previousblockhash, {"nextblockhash": block.hash})
        return block

    def insert_block(self, block):
        highest_block = self.db.get_highest_block()

        # If the db is empty create the coinbase block
        if highest_block is None:
            added_block = self._create_coinbase(block)
            return {
                "block": added_block,
                "fork": "",
                "reconverge": False
            }

        # Current block appends to the main chain
        if block.previousblockhash == highest_block.hash:
            added_block = self._append_to_main_chain(block)
            return {
                "block": added_block,
                "fork": "",
                "reconverge": False
            }
        # Current block is a fork
        else:
            fork_point = self.db.get_block_by_hash(block.previousblockhash)

            if fork_point.chain == MAIN_CHAIN:
                block = self._create_fork_of_main_chain(block, fork_point)
            else:
                block = self._grow_sidechain(block, fork_point)

            if block.chainwork > highest_block.chainwork:
                block = self.reconverge(block)

                return {
                    "block": block,
                    "fork": fork_point.hash,
                    "reconverge": True
                }
            else:
                return {
                    "block": block,
                    "fork": fork_point.hash,
                    "reconverge": False
                }

    def reconverge(self, new_top_block):
        print "[RECONVERGE] New top block is now %s" % new_top_block
        sidechain_blocks = sorted(self.db.get_blocks_by_chain(chain=new_top_block.chain), key=lambda b: b.height)

        sidechain_blocks.append(new_top_block)

        first_in_sidechain = sidechain_blocks[0]
        fork_point = self.db.get_block_by_hash(first_in_sidechain.previousblockhash)
        main_chain_blocks = self.db.get_blocks_higher_than(height=fork_point.height)

        new_sidechain_id = self._get_unique_chain_identifier()
        for block in main_chain_blocks:
            self.db.update_block(block.hash, {"chain": new_sidechain_id})

        for block in sidechain_blocks:
            self.db.update_block(block.hash, {"chain": MAIN_CHAIN})
        self.db.update_block(fork_point.hash, {"nextblockhash": first_in_sidechain.hash})

        new_top_block.chain = MAIN_CHAIN
        self.db.set_highest_block(new_top_block)
        return new_top_block


class BlockchainSyncer(object):
    """
    Supports syncing from block dat files and using RPC.
    """
    def __init__(self, database, blockchain, blocks_dir, rpc_client, stream_sync_limit=STREAM_SYNC_LIMIT_DEFAULT):
        # Instance of MongoDatabaseGateway (to keep track of syncs)
        self.db = database

        # Reference to the Blockchain interactor
        self.blockchain = blockchain

        # Find all of the block dat files inside the given block directory
        if os.path.isdir(blocks_dir):
            self.blk_files = sorted(
                [os.path.join(blocks_dir, f) for f in os.listdir(blocks_dir) if is_block_file(f)]
            )
        else:
            raise Exception("[BLOCKCHAIN_INIT] Given path is not a directory")

        self.sync_progress = 0

        # When to stop reading from .dat files and start syncing from RPC
        self.stream_sync_limit = stream_sync_limit

        # Client RPC connection
        self.rpc = rpc_client

    def _update_sync_progress(self):
        client_height = self.rpc.getblockcount()
        highest_known = self.db.get_highest_block()

        if highest_known:
            self.sync_progress = float(highest_known.height * 100) / client_height
        else:
            self.sync_progress = 0

    ######################
    # SYNC METHODS       #
    ######################
    def sync_auto(self, limit=None):
        start_time = datetime.datetime.now()
        print "[SYNC_STARTED] %s" % start_time

        self._update_sync_progress()

        if self.sync_progress < self.stream_sync_limit:
            self.sync_stream(sync_limit=limit)

        self._update_sync_progress()

        if self.sync_progress >= self.stream_sync_limit and self.sync_progress < 100:
            self.sync_rpc()

        end_time = datetime.datetime.now()
        diff_time = end_time - start_time
        print "[SYNC_COMPLETE] %s, duration: %s seconds" % (end_time, diff_time.total_seconds())

    def sync_stream(self, sync_limit):
        print "[SYNC_STREAM] Started sync from .dat files"
        highest_known = self.db.get_highest_block()

        blocks_in_db = 0
        if highest_known:
            blocks_in_db = highest_known.height

        client_height = self.rpc.getblockcount()
        limit_calc = (client_height - blocks_in_db) * (self.stream_sync_limit - self.sync_progress)
        if sync_limit:
            limit = min([sync_limit, limit_calc])
        else:
            limit = limit_calc

        import pdb
        pdb.set_trace()
        # Continue parsing where we left off
        if highest_known:
            self.blk_files = self.blk_files[highest_known.dat["index"]:]

        parsed = 0
        for (i, f) in enumerate(self.blk_files):
            stream = open(f, 'r')

            # Seek to the end of the last parsed block in the first iteration
            if i == 0 and highest_known:
                stream.seek(highest_known.dat['end'])

            while has_length(stream, 80) and parsed < limit:
                # parse block from stream
                block = BlockFactory.from_stream(stream)
                self.blockchain.insert_block(block)
                parsed += 1

                if block.height % 1000 == 0:
                    self._print_progress()

        self.db.flush_cache()
        return parsed

    def sync_rpc(self):
        print "[SYNC_RPC] Started sync from rpc"

        our_highest_block = self.db.get_highest_block()
        rpc_block = self.rpc.getblock(our_highest_block.hash)
        rpc_block_transactions = [
            self.rpc.getrawtransaction(tr, 1) for tr in rpc_block['tx']
        ]
        block = BlockFactory.from_rpc(rpc_block, rpc_block_transactions)

        while block.nextblockhash:
            rpc_block = self.rpc.getblock(block.nextblockhash)
            rpc_block_transactions = [
                self.rpc.getrawtransaction(tr, 1) for tr in rpc_block['tx']
            ]
            block = BlockFactory.from_rpc(rpc_block, rpc_block_transactions)
            self.blockchain.insert_block(block)

        self.db.flush_cache()

    ######################
    #  HELPER FUNCTIONS  #
    ######################
    def _print_progress(self):
        self._update_sync_progress()
        print "Progress: %s%%" % self.sync_progress

    def _should_stream_sync(self, stream, limit, parsed):
        return self.sync_progress < self.rpc_sync_percent and \
            has_length(stream, 80) and (limit == 0 or parsed < limit)
