import os
from factories import BlockFactory, TransactionFactory
from gamecredits.helpers import has_length, is_block_file, calculate_target, calculate_work
import datetime

MAIN_CHAIN = 0
PERSIST_EVERY = 1000  # blocks
RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"
RPC_SYNC_PERCENT_DEFAULT = 97
MIN_STREAM_THRESH = 1500000


class Blockchain(object):
    def __init__(self, database):
        # Instance of MongoDatabaseGateway
        self.db = database

        # Flag to check if sync is in the first iteration
        self.first_iter = True

    def insert_block(self, block):
        # If the chain_peak is None the db is empty
        if not self.chain_peak:
            block.height = 0
            block.chainwork = block.work
            block.chain = MAIN_CHAIN
            self.chain_peak = block
            self.first_iter = False
            return block

        # Current block appends to the main chain
        if block.previousblockhash == self.chain_peak.hash:
            self.chain_peak.nextblockhash = block.hash

            if not self.first_iter:
                self.db.put_block(self.chain_peak)

            block.height = self.chain_peak.height + 1
            block.chainwork = self.chain_peak.chainwork + block.work
            block.chain = MAIN_CHAIN
            self.chain_peak = block
        # Current block is a fork
        else:
            fork_point = self.db.get_block(block.previousblockhash)

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
                block.chain = self.num_forks
                self.db.update_block(block.previousblockhash, {"nextblockhash": block.hash})

            if block.chainwork > self.chain_peak.chainwork:
                print "[RECONVERGE] Reconverge, new top is now %s" % block.hash

                # Persist the previous block
                self.db.put_block(self.chain_peak)

                self.chain_peak = block
                block = self.reconverge(block)
            else:
                if not self.first_iter:
                    self.db.put_block(block)

        self.first_iter = False
        return block

    def reconverge(self, new_top_block):
        new_top_block.chain = MAIN_CHAIN
        first_in_sidechain_hash = new_top_block.hash
        current = self.db.get_block(new_top_block.previousblockhash)

        # Traverse up to the fork point and mark all nodes in sidechain as
        # part of main chain
        while current.chain != MAIN_CHAIN:
            self.db.update_block(current.hash, {"chain": MAIN_CHAIN})
            parent = self.db.get_block(current.previousblockhash)

            if parent.chain == MAIN_CHAIN:
                first_in_sidechain_hash = current.hash

            current = parent

        # Save the fork points hash
        fork_point_hash = current.hash

        # Traverse down the fork point and mark all main chain nodes part
        # of the sidechain
        while current.nextblockhash is not None:
            next_block = self.db.get_block(current.nextblockhash)
            self.db.update_block(next_block.hash, {"chain": self.num_forks + 1})
            current = next_block

        self.db.update_block(fork_point_hash, {"nextblockhash": first_in_sidechain_hash})

        self.num_convergences += 1

        return new_top_block

    def _find_reconverge_point(self, start):
        our_block = self.db.get_block(start.previousblockhash, no_cache=True)
        rpc_block = BlockFactory.from_rpc(self.rpc.getblock(our_block.hash))

        while not our_block == rpc_block:
            our_block = self.db.get_block(our_block.previousblockhash, no_cache=True)
            rpc_block = BlockFactory.from_rpc(self.rpc.getblock(our_block.hash))

        return (our_block, rpc_block)

    def _follow_chain_and_insert(self, start, limit=0):
        """
        Follow nextblockhash links and insert new RPC blocks into the DB
        """
        current = start
        inserted = 0
        client_height = self.rpc.getblockcount()

        while current is not None and (limit == 0 or inserted < limit):
            current.chain = MAIN_CHAIN
            current.target = calculate_target(current.bits)
            current.work = calculate_work(current.target)
            current.difficulty = float(current.difficulty)

            block_transactions = [
                TransactionFactory.from_rpc(self.rpc.getrawtransaction(tr, 1)) for tr in current.tx
            ]

            current.total = sum([tr.total for tr in block_transactions])

            self.db.put_block(current)
            self.db.put_transactions(block_transactions)

            if current.nextblockhash:
                current = BlockFactory.from_rpc(self.rpc.getblock(current.nextblockhash))
                # Update and print progress if necessary
                self._update_progress(current.height, client_height)
            else:
                current = None

            inserted += 1

            if inserted % 500 == 0:
                self._print_progress()

        return inserted

    def _follow_chain_and_delete(self, start):
        """
        Delete all blocks from the given block to the end of the chain
        """
        current = start

        deleted = 0
        while current is not None:
            self.delete_block(current.hash)
            deleted += 1

            if current.nextblockhash:
                current = self.get_block(current.nextblockhash)
            else:
                current = None

        return deleted


class ExploderSyncer(object):
    """
    Supports syncing from block dat files and using RPC.
    """
    def __init__(self, database, blockchain, blocks_dir, rpc_client, rpc_sync_percent=RPC_SYNC_PERCENT_DEFAULT):
        # Num of forks encountered while building the tree
        self.num_forks = 0

        # Num of reconvergences done while building the tree
        self.num_convergences = 0

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
        self.rpc_sync_percent = rpc_sync_percent

        # Client RPC connection
        self.rpc = rpc_client

    ######################
    # SYNC METHODS       #
    ######################
    def sync_auto(self, limit=0):
        start_time = datetime.datetime.now()
        print "[SYNC_STARTED] %s" % start_time

        client_height = self.rpc.getblockcount()
        highest_known = self.db.highest_block

        if highest_known:
            self.sync_progress = float(highest_known.height * 100) / client_height
        else:
            self.sync_progress = 0

        parsed = 0
        if (highest_known and highest_known.height < MIN_STREAM_THRESH) or self.sync_progress < self.rpc_sync_percent:
            parsed = self._sync_stream(highest_known, client_height, limit)

        if (limit == 0 or parsed < limit):
            self._sync_rpc(client_height, limit)

        end_time = datetime.datetime.now()
        diff_time = end_time - start_time
        print "[SYNC_COMPLETE] %s, duration: %s seconds" % (end_time, diff_time.total_seconds())

    def sync_stream(self, highest_known, client_height, limit):
        print "[SYNC_STREAM] Started sync from .dat files"
        parsed = 0

        # Continue parsing where we left off
        if highest_known:
            self.blk_files = self.blk_files[highest_known.dat["index"]:]
            self._update_progress(highest_known.height, client_height)

        for (i, f) in enumerate(self.blk_files):
            stream = open(f, 'r')

            # Seek to the end of the last parsed block in the first iteration
            if i == 0 and highest_known:
                stream.seek(highest_known.dat['end'])

            while self._should_stream_sync(stream, limit, parsed):
                # parse block from stream
                res = BlockFactory.from_stream(stream)

                # Persist block and transactions
                block = self.handle_stream_block(res['block'])
                self.db.put_transactions(res['transactions'])

                parsed += 1

                # Update and print progress if necessary
                self._update_progress(block.height, client_height)

                if block.height % 1000 == 0:
                    self._print_progress()

        self.db.flush_cache()
        return parsed

    def sync_rpc(self, client_height, limit):
        print "[SYNC_RPC] Started sync from rpc"

        our_highest_block = self.db.highest_block
        our_highest_block_in_rpc = self._get_rpc_block_by_hash(our_highest_block.hash)

        # Compare our highest known block to it's repr in RPC
        # if they have the same height and previousblockhash there was no reconverge
        # and we can just insert the blocks sequentially by following the nextblockhash links
        if our_highest_block == our_highest_block_in_rpc:
            if our_highest_block_in_rpc.nextblockhash:
                next_block = self._get_rpc_block_by_hash(our_highest_block_in_rpc.nextblockhash)
                self.db.update_block(our_highest_block.hash, {"nextblockhash": next_block.hash})
                self._follow_chain_and_insert(start=next_block, limit=limit)
        else:
            print("[SYNC_RPC] Reconverge")
            # Else find the reconverge point by going backwards and finding the first block
            # that is the same in our db and rpc and then sync upwards from there
            (our_block, rpc_block) = self._find_reconverge_point(start=our_highest_block)

            # Delete all blocks upwards from reconverge point (including the point)
            self._follow_chain_and_delete(our_block)

            # Insert all blocks from rpc to the end of the chain
            self._follow_chain_and_insert(rpc_block, limit=limit)

        self.db.flush_cache()

    ######################
    #  HELPER FUNCTIONS  #
    ######################
    def _update_progress(self, current_height, client_height):
        self.sync_progress = float(current_height * 100) / client_height

    def _print_progress(self):
        print "Progress: %s%%" % self.sync_progress

    def _should_stream_sync(self, stream, limit, parsed):
        return self.sync_progress < self.rpc_sync_percent and \
            has_length(stream, 80) and (limit == 0 or parsed < limit)
