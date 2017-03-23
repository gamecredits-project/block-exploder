import sys
from collections import deque
from pymongo import MongoClient
from factories import BlockFactory, VinFactory, VoutFactory

MAIN_CHAIN = 0
PERSIST_EVERY = 1000  # blocks


# TODO: Rename to blockchain
# it is a data structure that represents a blockchain
# and is persisted to a DB
class ChainTree(object):
    def __init__(self, block_db, tr_db, vin_db, vout_db):
        # Ref. to the root of the tree
        self.coinbase = None

        # Ref. to the highest node in the best chain
        self.best_chain = None

        # Num of forks encountered while building the tree
        self.num_forks = 0

        # Num of reconvergences done while building the tree
        self.num_convergences = 0

        # Dictionary of known hashes, used to check for orphan blocks
        # TODO: replace with check to block_cache and check to db in case of cache miss
        self.known_hashes = {}

        # Databases to persist the blockchain
        self.block_db = block_db
        self.tr_db = tr_db
        self.vin_db = vin_db
        self.vout_db = vout_db

        # Caches for batch writing
        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

        # Factories
        self.block_factory = BlockFactory()
        self.vin_factory = VinFactory()
        self.vout_factory = VoutFactory()

    def add_block(self, block):
        if self.coinbase is None:
            self.coinbase = ChainTreeNode(block.hash, None, block.block_work, MAIN_CHAIN, 0, [])
            self.best_chain = self.coinbase

            block.chainwork = self.coinbase.chainwork
            block.height = self.coinbase.height
            self.persist_block(block=block, chain=self.coinbase.chain)
            return self.coinbase

        # TODO: Check for orphans!?

        new_node = None
        # if previous is the top of the best chain just append it to the chain
        if block.previousblockhash == self.best_chain.block_hash:
            new_node = ChainTreeNode(
                block.hash,
                self.best_chain,
                self.best_chain.chainwork + block.block_work,
                MAIN_CHAIN,
                self.best_chain.height + 1,
                []
            )
            self.best_chain.append_child(new_node)
            self.best_chain = new_node

            block.chainwork = new_node.chainwork
            block.height = new_node.height
            self.persist_block(block=block, chain=new_node.chain)
            self.update_block(block.previousblockhash, {"nextblockhash": block.hash})
        # else traverse up the tree until you find the previous
        # and make a fork
        else:
            fork_point = self.best_chain.find_node(block.previousblockhash)

            if not fork_point:
                raise Exception("[ORPHAN] Block hash %s not found" % block.previousblockhash)

            if fork_point.chain == MAIN_CHAIN:
                # A fork of the main chain has happened
                print "[FORK] Fork on block %s" % block.previousblockhash
                self.num_forks += 1
                new_node_chain = self.num_forks
            else:
                print "[FORK_GROW] A sidechain is growing."
                new_node_chain = self.num_forks
                self.update_block(block.previousblockhash, {"nextblockhash": block.hash})

            new_node = ChainTreeNode(
                block.hash,
                fork_point,
                fork_point.chainwork + block.block_work,
                new_node_chain,
                fork_point.height + 1,
                []
            )

            fork_point.append_child(new_node)

            block.chainwork = new_node.chainwork
            block.height = new_node.height

            self.persist_block(block=block, chain=new_node.chain)

            if new_node.chainwork > self.best_chain.chainwork:
                print "[RECONVERGE] Reconverge, new top is now %s" % new_node.block_hash
                self.best_chain = new_node

                self.reconverge(block)

        return new_node

    def persist_block(self, block, chain):
        # Write block to cache and flush to database if necessary
        # If block is on the main chain write his trs, vins and vouts
        mongo_block = self.block_factory.parsed_to_dict(block, chain)

        # Persist the block
        self.block_cache[block.hash] = mongo_block

        self.persist_block_transactions(block)

        if len(self.block_cache) >= PERSIST_EVERY:
            # Flush cache to db
            self.flush_cache()

    def persist_block_transactions(self, block, flush=False):
        # Persist trs, vins and outs
        for tr in block.tx:
            self.tr_cache.append(tr.to_dict())

            for vin in tr.vin:
                self.vin_cache.append(self.vin_factory.parsed_to_mongo(vin, tr.txid))

            for (i, vout) in enumerate(tr.vout):
                self.vout_cache += self.vout_factory.parsed_to_mongo(vout, tr.txid, i)

        if flush:
            self.flush_cache()

    def flush_cache(self):
        self.block_db.insert_many(self.block_cache.values())
        self.tr_db.insert_many(self.tr_cache)
        self.vin_db.insert_many(self.vin_cache)
        self.vout_db.insert_many(self.vout_cache)

        self.block_cache = {}
        self.tr_cache = []
        self.vin_cache = []
        self.vout_cache = []

    def reconverge(self, new_top_block):
        current = self.find_block(new_top_block.hash)

        # Traverse up to the fork point and mark all nodes in sidechain as
        # part of main chain
        while current['chain'] != MAIN_CHAIN:
            self.update_block(current['hash'], {"chain": MAIN_CHAIN})
            parent = self.find_block(current['previousblockhash'])

            if parent['chain'] == MAIN_CHAIN:
                first_in_sidechain_hash = current['hash']

        # Save tne fork points hash
        fork_point_hash = current['hash']

        # Traverse down the fork point and mark all main chain nodes part
        # of the sidechain
        while 'nextblockhash' in current:
            next_block = self.find_block(current['nextblockhash'])
            self.update_block(next_block['hash'], {"chain": self.num_forks + 1})
            current = next_block

        self.update_block(fork_point_hash, {"nextblockhash": first_in_sidechain_hash})

    def find_block(self, block_hash):
        """
        Tries to find it in cache and if it misses finds it in the DB
        """
        if block_hash in self.block_cache:
            return self.block_cache[block_hash]

        mongo_block = self.block_db.find_one({"hash": block_hash})

        if not mongo_block:
            raise Exception("[FIND_BLOCK_FAILED] Block with hash %s not found." % block_hash)

        return mongo_block

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

    def add_node(self, previous_hash, next_hash, block_work):
        if self.coinbase is None:
            self.coinbase = ChainTreeNode(next_hash, None, block_work, 0, [])
            self.best_chain = self.coinbase
            self.known_hashes[next_hash] = True
            return self.coinbase

        if previous_hash not in self.known_hashes:
            raise Exception("[ORPHAN] %s" % previous_hash)

        new_node = None
        # if previous is main chain peak
        # just append it to the peak
        if previous_hash == self.best_chain.block_hash:
            new_node = ChainTreeNode(
                next_hash,
                self.best_chain,
                self.best_chain.chainwork + block_work,
                self.best_chain.height + 1,
                []
            )
            self.best_chain.append_child(new_node)
            self.best_chain = new_node
        # else traverse up the tree until you find the previous
        # and make a fork
        else:
            print "[FORK] Fork on block %s" % previous_hash
            fork_point = self.best_chain.find_node(previous_hash)

            if not fork_point:
                raise Exception("[ORPHAN] Block hash %s not found" % previous_hash)

            new_node = ChainTreeNode(
                next_hash,
                fork_point,
                fork_point.chainwork + block_work,
                fork_point.height + 1,
                []
            )

            fork_point.append_child(new_node)

            if new_node.chainwork > self.best_chain.chainwork:
                print "[RECONVERGE] Reconverge, new top is now %s" % new_node.block_hash
                self.best_chain = new_node

        self.known_hashes[next_hash] = True
        return new_node

    def print_tree(self):
        self.coinbase.print_node()


class ChainTreeNode(object):
    def __init__(self, block_hash, parent, chainwork, chain, height=0, children=[]):
        self.block_hash = block_hash
        self.parent = parent
        self.height = height
        self.children = children
        self.chainwork = chainwork
        self.chain = chain

    def append_child(self, node):
        self.children.append(node)

    def print_node(self):
        sys.stdout.write("-" * (self.height + 1))
        sys.stdout.write(" block_hash: %s, height: %s, children: %s\n"
                         % (self.block_hash, self.height, len(self.children)))

        for child in self.children:
            child.print_node()

    def find_node(self, block_hash):
        nodes_to_visit = deque([self])
        visited = []

        while nodes_to_visit:
            current = nodes_to_visit.popleft()
            nodes_to_visit += [ch for ch in current.children if ch not in visited and ch not in nodes_to_visit]

            if current.parent not in visited and current.parent not in nodes_to_visit:
                nodes_to_visit.append(current.parent)

            if current.block_hash == block_hash:
                return current

            visited.append(current)

        return None

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.block_hash == other.block_hash
        return False

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)
