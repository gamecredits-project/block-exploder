import struct
import json
import copy
import hashlib
import binascii

PATH_TO_SOME_DAT = '/home/vagrant/.gamecredits/blocks/blk00001.dat'


def uint1(stream):
    return ord(stream.read(1))


def uint2(stream):
    return struct.unpack('H', stream.read(2))[0]


def uint4(stream):
    return struct.unpack('I', stream.read(4))[0]


def uint8(stream):
    return struct.unpack('Q', stream.read(8))[0]


def hash32(stream):
    return bin_to_hex(stream.read(32))


def bin_to_hex(bin):
    return ''.join(('%x' % ord(a)) for a in bin[::-1])

def varint(stream):
    size = uint1(stream)

    if size < 0xfd:
        return size

    if size == 0xfd:
        return uint2(stream)

    if size == 0xfe:
        return uint4(stream)

    if size == 0xff:
        return uint8(stream)

    return -1


def has_length(self, stream, size):
    curPos = stream.tell()
    stream.seek(0, 2)

    fileSize = stream.tell()
    stream.seek(curPos)

    tempBlockSize = fileSize - curPos
    print tempBlockSize
    if tempBlockSize < size:
        return False
    return True


class Block(object):
    def __init__(self, index, stream):
        # Block height
        self.height = index
        # Skip first 4 bytes bcs the contain the magic number
        # which is a protocol identifier and always the same
        stream.seek(4, 1)
        # Size of this block in bytes
        self.size = uint4(stream)
        # Block header
        self.header = BlockHeader(stream)
        # Number of transactions in this block
        self.txcount = varint(stream)
        # Block transactions
        self.tx = [Transaction(stream) for i in range(0, self.txcount)]

    def to_dict(self):
        formatted = copy.deepcopy(self.__dict__)
        formatted['header'] = formatted['header'].to_dict()

        for i in range(0, len(formatted['tx'])):
            formatted['tx'][i] = formatted['tx'][i].to_dict()

        return formatted



    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class BlockHeader(object):
    def __init__(self, stream):
        # Calculate the block hash from the header
        header_bytes = stream.read(80)
        self.hash = hashlib.sha256(hashlib.sha256(header_bytes).digest()).digest()
        self.hash = self.hash[::-1].encode('hex_codec')

        # Rewind 80 bytes back so I can parse stuff
        stream.seek(-80, 1)

        # A version number to track software/protocol upgrades
        self.version = uint4(stream)
        # A reference to the hash of the previous (parent) block in the chain
        self.previousblockhash = hash32(stream)
        # A hash of the root of the merkle tree of this blocks transactions
        self.merkleroot = hash32(stream)
        # The approximate creation time of this block (seconds from Unix Epoch)
        self.time = uint4(stream)
        # Difficulty target
        self.bits = hex(uint4(stream))
        # A counter used for the proof-of-work algorithm
        self.nonce = uint4(stream)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class Transaction(object):
    def __init__(self, stream):
        self.version = uint4(stream)
        self.vin_count = varint(stream)
        self.vin = [TransactionInput(stream) for i in range(0, self.vin_count)]
        self.vout_count = varint(stream)
        self.vout = [TransactionOutput(stream) for i in range(0, self.vout_count)]
        self.locktime = uint4(stream)

    def to_dict(self):
        formatted = copy.deepcopy(self.__dict__)

        for i in range(0, len(formatted['vin'])):
            formatted['vin'][i] = formatted['vin'][i].to_dict()

        for i in range(0, len(formatted['vout'])):
            formatted['vout'][i] = formatted['vout'][i].to_dict()

        return formatted

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class TransactionInput(object):
    def __init__(self, stream):
        self.prevhash = hash32(stream)
        self.tx_out_id = uint4(stream)
        self.script_len = varint(stream)
        self.script_sig = bin_to_hex(stream.read(self.script_len))
        self.sequence_number = uint4(stream)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class TransactionOutput(object):
    def __init__(self, stream):
        self.value = uint8(stream)
        self.script_len = varint(stream)
        self.public_key = bin_to_hex(stream.read(self.script_len))

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


if __name__ == "__main__":
    print "It works"

    blockchain = open(PATH_TO_SOME_DAT, 'r')

    for i in range(0, 10):
        print Block(i, blockchain)
