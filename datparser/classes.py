import json
import copy
import binascii
import enum

from helpers import *
from pybitcointools import bin_to_b58check, pubkey_to_address


# GameCredits specific constants
GAME_MAGIC_BYTE = 38
PAY_TO_SCRIPT_MAGIC_BYTE = 5
MAX_DIFFICULTY = int("0x00000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF", 16)


# Operator types for output script parsing
class ScriptOperator(enum.Enum):
    OP_CHECKSIG = "ac"
    OP_DUP = "76"
    OP_HASH160 = "a9"
    OP_EQUAL = "87"
    OP_EQUALVERIFY = "88"
    OP_RETURN = "6a"


class ParsedBlock(object):
    def __init__(self, stream):
        # Skip first 4 bytes bcs the contain the magic number
        # which is a protocol identifier and always the same
        stream.seek(4, 1)

        # Size of this block in bytes
        self.size = uint4(stream)

        # Parse the block header
        header = ParsedBlockHeader(stream)

        # Unpack the header - shorthand for writing bunch of assignments liked
        # self.hash = header.hash
        for (key, val) in header.__dict__.iteritems():
            setattr(self, key, val)

        # Number of ParsedTransactions in this block
        txcount = varint(stream)

        try:
            # First ParsedTransaction in a block is a "coinbase" transction
            # that transfers newly generated coins to a miner
            # and has a slightly different input format
            self.tx = [ParsedTransaction(stream, coinbase=True)]

            # Append other ParsedTransactions (if there are any)
            for i in range(1, txcount):
                self.tx.append(ParsedTransaction(stream))
        except Exception:
            print "Problematic block: %s" % self.header.hash
            raise

        self.chain = None

    @property
    def block_work(self):
        # Block work is calculated as 2^256 / (target + 1)
        # rounded down to the nearest integer
        # See the GetBlockWork() function in the main.h file
        # https://github.com/gamecredits-project/GameCredits/blob/4c1844a3ffecfbd222ee68cbac1f1fc7ec2072e5/src/main.h
        return int(float(2 ** 256) / (self.target + 1))

    def to_dict(self):
        formatted = copy.deepcopy(self.__dict__)

        for i in range(0, len(formatted['tx'])):
            formatted['tx'][i] = formatted['tx'][i].to_dict()

        return formatted

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class ParsedBlockHeader(object):
    def __init__(self, stream):
        # Calculate the block hash from the header
        header_bytes = stream.read(80)
        self.hash = double_sha(header_bytes, reverse=True)

        # Rewind 80 bytes back so I can parse stuff
        # OPTIMIZE: use io.BytesIO to pass bytes as a stream
        stream.seek(-80, 1)

        # A version number to track software/protocol upgrades
        self.version = uint4(stream)

        # A reference to the hash of the previous (parent) block in the chain
        self.previousblockhash = hash32(stream)

        # A hash of the root of the merkle tree of this blocks ParsedTransactions
        self.merkleroot = hash32(stream)[::-1]

        # The approximate creation time of this block (seconds from Unix Epoch)
        self.time = uint4(stream)

        # Difficulty bits in hexadeximal format
        # This notation expresses the difficulty target as a coefficient/exponent format,
        # with the first two hexadecimal digits for the exponent
        # and the rest as the coefficient.
        self.bits = hex(uint4(stream))

        # Extract exponent and coefficient from bits
        exp = int(self.bits[2:4], 16)
        coef = int(self.bits[4:], 16)

        # Calculate target, formula from Mastering Bitcoin book
        self.target = coef * 2 ** (8 * (exp - 3))

        # Difficulty is calculated as a ratio between the maximum allowed difficulty
        # and the blocks difficulty target
        self.difficulty = round(float(MAX_DIFFICULTY) / self.target, 8)

        # A counter used for the proof-of-work algorithm
        self.nonce = uint4(stream)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class ParsedTransaction(object):
    def __init__(self, stream, coinbase=False):
        tr_start = stream.tell()

        # A version number to track software/protocol upgrades
        self.version = uint4(stream)

        # Number of inputs in this ParsedTransaction
        vin_count = varint(stream)

        skip = 0
        # Parse the coinbase input
        if coinbase:
            self.vin = [ParsedTransactionInput(stream, coinbase=True)]
            skip = 1
        else:
            self.vin = []

        # Parse other inputs (if they exist)
        for i in range(skip, vin_count):
            self.vin.append(ParsedTransactionInput(stream))

        # Number of outputs in this transction
        vout_count = varint(stream)

        # Parse the ParsedTransaction outputs
        self.vout = [ParsedTransactionOutput(stream) for i in range(0, vout_count)]

        # ParsedTransaction locktime
        self.locktime = uint4(stream)

        tr_end = stream.tell()

        # rewind so we can calculate the txid
        # OPTIMIZE: use io.BytesIO to pass bytes as a stream
        stream.seek(tr_start)
        tr_bytes = stream.read(tr_end - tr_start)
        self.txid = double_sha(tr_bytes, reverse=True)

        self.total = round(sum([vout.value for vout in self.vout]), 8)

    def to_dict(self):
        formatted = copy.deepcopy(self.__dict__)

        for i in range(0, len(formatted['vin'])):
            formatted['vin'][i] = formatted['vin'][i].to_dict()

        for i in range(0, len(formatted['vout'])):
            formatted['vout'][i] = formatted['vout'][i].to_dict()

        return formatted

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class ParsedTransactionInput(object):
    def __init__(self, stream, coinbase=False):
        if not coinbase:
            self.prev_txid = hash32(stream)
            self.vout_index = uint4(stream)
            script_len = varint(stream)
            self.hex = binascii.hexlify(stream.read(script_len))
            self.sequence = uint4(stream)
        else:
            # Throw away these values for coinbase ParsedTransactions
            _ = (hash32(stream), uint4(stream))

            script_len = varint(stream)
            self.coinbase = binascii.hexlify(stream.read(script_len))
            self.sequence = uint4(stream)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)


class ParsedTransactionOutput(object):
    def __init__(self, stream):
        # Value in satoshi, convert it to GAME
        self.value = uint8(stream) * 10e-9

        # Length of the script after this in bytes
        script_len = varint(stream)

        # Read script of length script_len
        # REMEMBER: use binascii not the custom bin_to_hex function
        # because bin_to_hex ignored zeroes for some reason
        self.hex = binascii.hexlify(stream.read(script_len))

        # Parse the script to extract addresses
        parsed = self.parse_script(self.hex)

        self.asm = parsed.get("asm")
        self.addresses = parsed.get("addresses")
        self.type = parsed.get("type")
        self.reqsigs = parsed.get("reqSigs")

    def parse_script(self, script):
        """
        Parses the bitcoin script - https://en.bitcoin.it/wiki/Script,
        currently supports only pay2pubkey and pay2pubkeyhash ParsedTransactions
        """
        if script[:4] == ScriptOperator.OP_DUP.value + ScriptOperator.OP_HASH160.value:
            # Pay to public key hash ParsedTransaction
            (pubkey, address) = self.parse_pay2pubkey_hash(script)
            return {
                "asm": "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG" % pubkey,
                "reqSigs": 1,
                "type": "pubkeyhash",
                "addresses": [address]
            }
        elif script[-2:] == ScriptOperator.OP_CHECKSIG.value:
            # Pay to public key ParsedTransaction (deprecated)
            (pubkey, address) = self.parse_pay2pubkey(script)
            return {
                "asm": "%s OP_CHECKSIG" % pubkey,
                "reqSigs": 1,
                "type": "pubkey",
                "addresses": [address]
            }
        elif script[:2] == ScriptOperator.OP_RETURN.value:
            # Nulldata ParsedTransaction - https://bitcoin.org/en/glossary/null-data-ParsedTransaction
            return {
                "asm": "OP_RETURN %s" % script[4:],
                "type": "nulldata"
            }
        elif script[:2] == ScriptOperator.OP_HASH160.value:
            # Pay to script hash ParsedTransaction - https://en.bitcoin.it/wiki/Pay_to_script_hash
            (pubkey, address) = self.parse_pay2scripthash(script)
            return {
                "asm": "OP_HASH160 %s OP_EQUAL" % pubkey,
                "reqSigs": 1,
                "type": "scripthash",
                "addresses": [address]
            }
        else:
            raise Exception("[PARSE_SCRIPT] Unknown script format: %s" % script)

    def parse_pay2pubkey(self, script):
        # First 2 bytes is num bytes to be pushed to the stack
        # Last 2 are OP_CHECKSIG, pubkey is in the middle
        pubkey = script[2:-2]

        # Create address from public key (HASH160 + B58_CHECK)
        address = pubkey_to_address(pubkey, magicbyte=GAME_MAGIC_BYTE)

        return (pubkey, address)

    def parse_pay2pubkey_hash(self, script):
        # Extract pubkey hash from script
        # First 2 bytes is OP_DUP, second 2 bytes is OP_HASH160
        # Then there are 2 bytes representing how much data is pushed to the stack (not important just skip them)
        # That's why we start at 6, last four bytes are OP_EQUALVERIFY and OP_CHECKSIG so we end at -4
        pubkey = script[6:-4]

        # Public Key Hash is equivalent to the GAME address,
        # it has been hashed twice but without the Base58Check encoding,
        # so we need only to encode it
        address = bin_to_b58check(binascii.unhexlify(pubkey), GAME_MAGIC_BYTE)

        return (pubkey, address)

    def parse_pay2scripthash(self, script):
        # First 2 bytes is OP_HASH160
        # Second 2 bytes is num bytes to be pushed to the stack
        # Then comes the pubkey
        pubkey = script[4:-2]

        # P2SH addresses use the version prefix 5, which results in
        # Base58Check-encoded addresses that start with a 3
        address = bin_to_b58check(binascii.unhexlify(pubkey), PAY_TO_SCRIPT_MAGIC_BYTE)

        return (pubkey, address)

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)
