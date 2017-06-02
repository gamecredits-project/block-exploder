import os
from gamecredits.helpers import has_length, is_block_file
import datetime
import time
import itertools
import logging
import requests
import json
from gamecredits.factories import BlockFactory
from gamecredits.constants import SUBSIDY_HALVING_INTERVAL
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

    ######################
    # SYNC METHODS       #
    ######################
    def sync_auto(self, limit=None):
        start_time = time.time()
        start_block = self.db.get_highest_block()

        self._update_sync_progress()

        if self.sync_progress < self.stream_sync_limit:
            self.sync_stream(sync_limit=limit)

        self._update_sync_progress()

        if self.sync_progress >= self.stream_sync_limit and self.sync_progress < 100:
            self.sync_rpc()

        end_block = self.db.get_highest_block()
        end_time = time.time()
        # Check if there were any new blocks
        if end_block.height > start_block.height:
            self.db.put_sync_history(start_time, end_time, start_block.height, end_block.height)

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

        # When a block is a part of a sidechain (fork) it has -1 confirmations
        while rpc_block['confirmations'] == -1:
            rpc_block = self.rpc.getblock(rpc_block['previousblockhash'])

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


class BlockchainAnalyzer(object):
    def __init__(self, database, rpc_client, config):
        self.db = database
        self.config = config
        # Client RPC connection
        self.rpc = rpc_client

    def get_network_hash_rate(self, end_time=None):
        highest = self.db.get_highest_block()
        if not end_time:
            end_time = highest.time
        start_time = end_time - 86400     # seconds in day
        blocks_in_interval = self.db.get_blocks_between_time(start_time, end_time)
        cum_work = sum([block['work'] for block in blocks_in_interval])
        hps = float(cum_work) / 86400
        return int(hps)

    def save_network_hash_rate(self, hash_rate, time=None):
        if hash_rate:
            self.db.put_hashrate(int(hash_rate), time)

    def get_supply(self):
        height = self.db.get_blockchain_height()
        reward = 50
        supply = 0
        while height > SUBSIDY_HALVING_INTERVAL:
            supply += SUBSIDY_HALVING_INTERVAL * reward
            height -= SUBSIDY_HALVING_INTERVAL
            reward /= 2

        supply += height * reward
        return supply

    def get_blockchain_size(self):
        """
        Walks (recursively) through the provided data directory
        and calculates the size of the whole directory
        """
        datadir_path = self.config.get('syncer', 'datadir_path')
        size = 0
        for root, dirs, files in os.walk(datadir_path):
            for file in files:
                size += os.stat(os.path.join(root, file)).st_size

        # Calculate size in GB
        B_IN_GB = pow(2, 30)
        size = float(size) / B_IN_GB
        return round(size, 2)

    def save_network_stats(self, supply, blockchain_size):
        if supply and blockchain_size:
            self.db.update_network_stats(supply=supply, blockchain_size=blockchain_size)

    def get_client_version(self):
        wallet_info = self.rpc.getinfo()
        return wallet_info['version']

    def get_peer_info(self):
        return self.rpc.getpeerinfo()

    def update_peer_location(self, peer_info):
        """
        Update peer info with latitude and longitude from freegeoip.net
        """
        for peer in peer_info:
            addr = peer["addr"]
            if addr:
                # Remove port from ip address
                ip = addr.split(':')[0]
                response = requests.get("%s/%s/%s" % (self.config.get('syncer', 'geo_ip_url'), "json", ip))
                json_data = json.loads(response.text)
                if json_data and json_data['latitude'] and json_data['longitude']:
                    peer['latitude'] = json_data['latitude']
                    peer['longitude'] = json_data['longitude']
        return peer_info

    def save_client_info(self, version, ip, peer_info):
        if version and peer_info:
            self.db.put_client_info(version=version, ip=ip, peer_info=peer_info)

    def calculate_sync_progress(self):
        client_height = self.rpc.getblockcount()
        highest_known = self.db.get_highest_block()

        if highest_known:
            progress = float(highest_known.height * 100) / client_height
        else:
            progress = 0

        return round(progress, 2)

    def update_sync_progress(self, progress):
        if progress:
            self.db.update_sync_progress(progress=progress)

    def get_game_price(self):
        """
        Return GameCredits USD price from coinmarketcap
        """
        response = requests.get(self.config.get('syncer', 'game_price_url'))
        json_data = json.loads(response.text)[0]
        if json_data and json_data['price_usd']:
            return float(json_data['price_usd'])
        return None

    def save_game_price(self, price):
        if price:
            self.db.update_game_price(price)
