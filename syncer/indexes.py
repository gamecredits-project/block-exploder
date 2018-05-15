import os
import sys
from binascii import hexlify
import struct
import plyvel


import logging
# TEST CLASS

class BlockIndex(object):
    def __init__(self, hash, height, file_no, data_pos):
        self.hash = hash
        self.height = height
        self.file = file_no
        self.data_pos = data_pos

    def __repr__(self):
        return "DBBlockIndex(%s, height=%d, file_no=%d, file_pos=%d)" \
               % (self.hash, self.height, self.file, self.data_pos)

class BlockIndexes(object):
    def __init__(self, blk_path, block_factory):
        self.blk_path = blk_path
        self.index_path = blk_path + '/indext'

        # Instance of Gamecredits python module BlockFactory
        self.block_factory = block_factory

        self.block_indexes = None

    # def _open_block_stream(self, blockfile, offset):
    #     stream = open(blockfile, 'rb')
    #     stream.seek(offset - 4)  # Size is present 4 bytes before the db offset
    #     size, = struct.unpack("<I", stream.read(4))
    #     stream.read(size)
    #     return stream

    def _get_block_indexes_from_db(self):
        """
        There is no method of leveldb to close the db (and release the lock).
        This creates problem during concurrent operations.
        This function also provides caching of indexes.
        """
        print "Usao"
        db = plyvel.DB(self.index_path, compression=None)
        self.block_indexes = [DBBlockIndex(format_hash(k[1:]), v)
                            for k, v in db.iterator() if ord(k[0]) == 98]
            
        db.close()
        self.block_indexes.sort(key=lambda x: x.height)
        return self.block_indexes

    # def _index_confirmed(self, chain_indexes, num_confirmations=6):
    #     """
    #     Check if the first block index in "chain_indexes" has at least
    #     "num_confirmation" (6) blocks built on top of it.
    #     If it doesn't it is not confirmed and is an orphan.
    #     """
    #     chains = []
    #     first_block = None

    #     for i, index in enumerate(chain_indexes):
    #         if index.file == -1 or index.data_pos == -1:
    #             return False

    #         blkFile = os.path.join(self.blk_path, "blk%05d.dat" % index.file)
    #         block_stream = self._open_block_stream(blkFile, index.data_pos)
    #         block = self.block_factory.from_stream(block_stream)
            
    #         if i == 0:
    #             first_block = block

    #         chains.append([block.hash])

    #         for chain in chains:
    #             if chain[-1] == block.previousblockhash:
    #                 chain.append(block.hash)
                    
    #             if len(chain) == num_confirmations:
    #                 if first_block.hash in chain:
    #                     return True
    #                 else:
    #                     return False

    # # For the future, test if we need to filter orphan blocks
    # def _indexes_without_orphan_blocks(self):
    #     """
    #     Yields the blocks contained in the .blk files as per
    #     the height extract from the leveldb index present at path
    #     index maintained by bitcoind.
    #     """

    #     orphans = []  # hold blocks that are orphans with < 6 blocks on top
    #     last_height = -1
    #     block_indexes_without_orphans = self._get_block_indexes_from_db()

    #     for i, blockIdx in enumerate(block_indexes_without_orphans):
    #         if last_height > -1:

    #             if blockIdx.height == last_height:

    #                 if self._index_confirmed(block_indexes_without_orphans[i:], self.blk_path):
    #                     orphans.append(block_indexes_without_orphans[i - 1].hash)
    #                 else:
    #                     orphans.append(block_indexes_without_orphans[i].hash)

    #         last_height = blockIdx.height

    #     # filter out the orphan blocks, so we are left only with block indexes
    #     # that have been confirmed
    #     # (or are new enough that they haven't yet been confirmed)
    #     block_indexes_without_orphans = list(filter(lambda block: block.hash not in orphans, self.block_indexes))
    #     return block_indexes_without_orphans

    def indexes_to_cache(self):
        self.block_indexes = self._get_block_indexes_from_db()

    def get_block_indexes_cache(self):
        return self.block_indexes

class DBBlockIndex(object):
    BLOCK_HAVE_DATA = 8
    BLOCK_HAVE_UNDO = 16
    
    def __init__(self, key, value):
        self.hash = key
        # decoded_value =  value.encode('hex') + '\n'
        pos = 0

        n_version, i = self.read_varint(value[pos:])
        pos += i

        self.height, i = self.read_varint(value[pos:])
        pos += i

        status, i = self.read_varint(value[pos:])
        pos += i

        n_tx, i = self.read_varint(value[pos:])
        pos += i

        self.file_no, i = self.read_varint(value[pos:])
        pos += i

        self.data_pos, i = self.read_varint(value[pos:])
        pos += i

        undo_pos, i = self.read_varint(value[pos:])
        pos += i

    def read_varint(self,raw_hex):
        """
        Reads the weird format of VarInt present in src/serialize.h of bitcoin core
        and being used for storing data in the leveldb.
        This is not the VARINT format described for general bitcoin serialization
        use.
        """
        n = 0
        pos = 0
        while True:
            data = raw_hex[pos]
            if sys.version_info < (3, 0):
                data = int(data.encode('hex'), 16)
            pos += 1
            n = (n << 7) | (data & 0x7f)
            if data & 0x80 == 0:
                return n, pos
            n += 1

    def __repr__(self):
        return "DBBlockIndex(hash=%s, height=%d, file_no=%d, file_pos=%d)" \
               % (self.hash, self.height, self.file_no, self.data_pos)

def format_hash(hash_):
    return str(hexlify(hash_[::-1]).decode("utf-8"))