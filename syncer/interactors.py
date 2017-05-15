import os
from gamecredits.helpers import has_length, is_block_file
import datetime
import itertools
import logging
from gamecredits.factories import BlockFactory
from bitcoinrpc.authproxy import JSONRPCException


class Blockchain(object):
    def __init__(self, database, config):
        self.config = config

        logging.basicConfig(
            filename=os.path.join(self.config.get('syncer', 'logs_dir'), 'blockchain-syncer.log'), level=logging.INFO
        )

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
        block.chain = self.config.get('syncer', 'main_chain')
        self.db.put_block(block)
        return block

    def _append_to_main_chain(self, block):
        chain_peak = self.db.get_block_by_hash(block.previousblockhash)

        block.height = chain_peak.height + 1
        block.chainwork = chain_peak.chainwork + block.work
        block.chain = self.config.get('syncer', 'main_chain')

        self.db.update_block(chain_peak.hash, {"nextblockhash": block.hash})
        self.db.put_block(block)
        return block

    def _create_fork_of_main_chain(self, block, fork_point):
        logging.info("[FORK] Fork on block %s" % block.previousblockhash)
        block.height = fork_point.height + 1
        block.chainwork = fork_point.chainwork + block.work
        block.chain = self._get_unique_chain_identifier()
        self.db.put_block(block)
        return block

    def _grow_sidechain(self, block, fork_point):
        logging.info("[FORK_GROW] A sidechain is growing.")
        block.height = fork_point.height + 1
        block.chainwork = fork_point.chainwork + block.work
        block.chain = fork_point.chain
        self.db.update_block(block.previousblockhash, {"nextblockhash": block.hash})
        self.db.put_block(block)
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

            if fork_point.chain == self.config.get('syncer', 'main_chain'):
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
        logging.info("[RECONVERGE] New top block is now %s" % new_top_block)
        sidechain_blocks = sorted(self.db.get_blocks_by_chain(chain=new_top_block.chain), key=lambda b: b.height)

        sidechain_blocks.append(new_top_block)

        first_in_sidechain = sidechain_blocks[0]
        fork_point = self.db.get_block_by_hash(first_in_sidechain.previousblockhash)
        main_chain_blocks = self.db.get_blocks_higher_than(height=fork_point.height)

        new_sidechain_id = self._get_unique_chain_identifier()
        for block in main_chain_blocks:
            self.db.update_block(block.hash, {"chain": new_sidechain_id})

        for block in sidechain_blocks:
            self.db.update_block(block.hash, {"chain": self.config.get('syncer', 'main_chain')})
        self.db.update_block(fork_point.hash, {"nextblockhash": first_in_sidechain.hash})

        new_top_block.chain = self.config.get('syncer', 'main_chain')
        self.db.set_highest_block(new_top_block)
        return new_top_block


class BlockchainSyncer(object):
    """
    Supports syncing from block dat files and using RPC.
    """
    def __init__(self, database, blockchain, rpc_client, config):
        self.config = config

        logging.basicConfig(
            filename=os.path.join(self.config.get('syncer', 'logs_dir'), 'blockchain-syncer.log'), level=logging.INFO
        )

        # Instance of MongoDatabaseGateway (to keep track of syncs)
        self.db = database

        # Reference to the Blockchain interactor
        self.blockchain = blockchain

        # Find all of the block dat files inside the given block directory
        if os.path.isdir(config.get('syncer', 'blocks_dir')):
            self.blk_files = sorted(
                [os.path.join(config.get('syncer', 'blocks_dir'), f)
                 for f in os.listdir(config.get('syncer', 'blocks_dir')) if is_block_file(f)]
            )
        else:
            raise Exception("[BLOCKCHAIN_INIT] Given path is not a directory")

        self.sync_progress = 0

        # When to stop reading from .dat files and start syncing from RPC
        self.stream_sync_limit = config.getint('syncer', 'stream_sync_limit')

        # Client RPC connection
        self.rpc = rpc_client

    def _update_sync_progress(self):
        client_height = self.rpc.getblockcount()
        highest_known = self.db.get_highest_block()

        if highest_known:
            self.sync_progress = float(highest_known.height * 100) / client_height
        else:
            self.sync_progress = 0

    def calculate_network_hash_rate(self):
        highest = self.db.get_highest_block()
        end = highest.time
        start = highest.time - 86400     # seconds in day
        blocks_in_interval = self.db.get_blocks_between_time(start, end)
        cum_work = sum([block['work'] for block in blocks_in_interval])
        hps = float(cum_work) / 86400
        self.db.put_hashrate(int(hps))

    ######################
    # SYNC METHODS       #
    ######################
    def sync_auto(self, limit=None):
        self._update_sync_progress()

        if self.sync_progress < self.stream_sync_limit:
            self.sync_stream(sync_limit=limit)

        self._update_sync_progress()

        if self.sync_progress >= self.stream_sync_limit and self.sync_progress < 100:
            self.sync_rpc()

    def sync_stream(self, sync_limit):
        start_time = datetime.datetime.now()
        logging.info("[SYNC_STREAM_STARTED] %s" % start_time)
        highest_known = self.db.get_highest_block()

        blocks_in_db = 0
        if highest_known:
            blocks_in_db = highest_known.height

        client_height = self.rpc.getblockcount()
        limit_calc = int((client_height - blocks_in_db) * self.stream_sync_limit / 100)
        if sync_limit:
            limit = min([sync_limit, limit_calc])
        else:
            limit = limit_calc

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

        end_time = datetime.datetime.now()
        diff_time = end_time - start_time
        logging.info("[SYNC_STREAM_COMPLETE] %s, duration: %s seconds" % (end_time, diff_time.total_seconds()))
        return parsed

    def sync_rpc(self):
        start_time = datetime.datetime.now()
        logging.info("[SYNC_RPC_STARTED] %s" % start_time)

        our_highest_block = self.db.get_highest_block()

        rpc_block = None
        while rpc_block is None:
            try:
                rpc_block = self.rpc.getblock(our_highest_block.hash)
            except JSONRPCException:
                our_highest_block = self.db.get_block_by_hash(our_highest_block.previousblockhash)

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
        end_time = datetime.datetime.now()
        diff_time = end_time - start_time
        logging.info("[SYNC_RPC_COMPLETE] %s, duration: %s seconds" % (end_time, diff_time.total_seconds()))

    ######################
    #  HELPER FUNCTIONS  #
    ######################
    def _print_progress(self):
        self._update_sync_progress()
        logging.info("Progress: %s%%" % self.sync_progress)
