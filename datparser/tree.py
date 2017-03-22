import sys
from collections import deque
from pymongo import MongoClient

class ChainTree(object):
    def __init__(self):
        # Ref. to the root of the tree
        self.coinbase = None

        # Ref. to the highest node in the best chain
        self.best_chain = None

        # Num of forks encountered while building the tree
        self.num_forks = 0

        # Num of reconvergences done while building the tree
        self.num_convergences = 0

        # Dictionary of known hashes, used to check for orphan blocks
        self.known_hashes = {}

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
    def __init__(self, block_hash, parent, chainwork, height=0, children=[]):
        self.block_hash = block_hash
        self.parent = parent
        self.height = height
        self.children = children
        self.chainwork = chainwork

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


if __name__ == '__main__':
    tree = ChainTree()

    tree.add_node(
        previous_hash="618c1928-30ff-46c0-b16f-642537b927f1",
        next_hash="2cc9315b-1040-45f5-9336-28b1e4c2e70c"
    )

    tree.add_node(
        previous_hash="2cc9315b-1040-45f5-9336-28b1e4c2e70c",
        next_hash="e791bd23-7a65-4f9d-9288-16f95200a998"
    )

    tree.add_node(
        previous_hash="2cc9315b-1040-45f5-9336-28b1e4c2e70c",
        next_hash="972b60f8-2451-41ab-b942-21704ed14d29"
    )
    tree.print_tree()
