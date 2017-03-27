from helpers import *
import binascii
import enum

from pybitcointools import bin_to_b58check, pubkey_to_address

from classes import *

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


class BlockFactory(object):
    @staticmethod
    def _parse_block_header(stream):
        # Calculate the block hash from the header
        header_bytes = stream.read(80)
        block_hash = double_sha(header_bytes, reverse=True)

        # Rewind 80 bytes back so I can parse stuff
        # OPTIMIZE: use io.BytesIO to pass bytes as a stream
        stream.seek(-80, 1)

        # A version number to track software/protocol upgrades
        version = uint4(stream)

        # A reference to the hash of the previous (parent) block in the chain
        previousblockhash = hash32(stream)

        # A hash of the root of the merkle tree of this blocks ParsedTransactions
        merkleroot = hash32(stream)[::-1]

        # The approximate creation time of this block (seconds from Unix Epoch)
        time = uint4(stream)

        # Difficulty bits in hexadeximal format
        # This notation expresses the difficulty target as a coefficient/exponent format,
        # with the first two hexadecimal digits for the exponent
        # and the rest as the coefficient.
        bits = hex(uint4(stream))

        target = calculate_target(bits)

        # Difficulty is calculated as a ratio between the maximum allowed difficulty
        # and the blocks difficulty target
        difficulty = round(float(MAX_DIFFICULTY) / target, 8)

        # A counter used for the proof-of-work algorithm
        nonce = uint4(stream)

        # Block work is calculated as 2^256 / (target + 1)
        # rounded down to the nearest integer
        # See the GetBlockWork() function in the main.h file
        # https://github.com/gamecredits-project/GameCredits/blob/4c1844a3ffecfbd222ee68cbac1f1fc7ec2072e5/src/main.h
        work = calculate_work(target)

        return BlockHeader(
            hash=block_hash,
            version=version,
            previousblockhash=previousblockhash,
            merkleroot=merkleroot,
            time=time,
            bits=bits,
            target=target,
            difficulty=difficulty,
            nonce=nonce,
            work=work
        )

    @staticmethod
    def from_stream(stream):
        # Info about the dat file we parsed the block from
        dat = {
            "index": int(stream.name[-5:-4]),
            "start": stream.tell()
        }

        # Skip first 4 bytes bcs the contain the magic number
        # which is a protocol identifier and always the same
        stream.seek(4, 1)

        # Size of this block in bytes
        size = uint4(stream)

        # Parse the block header
        header = BlockFactory._parse_block_header(stream)

        # Number of ParsedTransactions in this block
        txcount = varint(stream)

        try:
            # First ParsedTransaction in a block is a "coinbase" transction
            # that transfers newly generated coins to a miner
            # and has a slightly different input format
            tx = [TransactionFactory.from_stream(stream, coinbase=True)]

            # Append other ParsedTransactions (if there are any)
            for i in range(1, txcount):
                tx.append(TransactionFactory.from_stream(stream))
        except Exception:
            print "Problematic block: %s" % header.hash
            raise

        total = sum([tr.total for tr in tx])

        dat["end"] = stream.tell()

        # Create the block
        return {
            "block": Block(
                size=size,
                header=header,
                tx=[tr.txid for tr in tx],
                dat=dat,
                total=total
            ),
            "transactions": tx
        }

    @staticmethod
    def from_mongo(mongo_block):
        header = BlockHeader(
            hash=mongo_block['hash'],
            version=mongo_block['version'],
            previousblockhash=mongo_block['previousblockhash'],
            merkleroot=mongo_block['merkleroot'],
            time=mongo_block['time'],
            bits=mongo_block['bits'],
            target=mongo_block['target'],
            difficulty=mongo_block['difficulty'],
            nonce=mongo_block['nonce'],
            work=mongo_block['work']
        )

        return Block(
            size=mongo_block['size'],
            header=header,
            tx=mongo_block['tx'],
            dat=mongo_block['dat'],
            nextblockhash=mongo_block['nextblockhash'],
            height=mongo_block['height'],
            chainwork=int(mongo_block['chainwork'], 16),
            chain=mongo_block['chain'],
            total=mongo_block['total']
        )

    @staticmethod
    def from_rpc(rpc_block):
        header = BlockHeader(
            hash=rpc_block['hash'],
            version=rpc_block['version'],
            previousblockhash=rpc_block['previousblockhash'],
            merkleroot=rpc_block['merkleroot'],
            time=rpc_block['time'],
            bits='0x' + rpc_block['bits'],  # We use 0x repr for hex strings
            difficulty=rpc_block['difficulty'],
            nonce=rpc_block['nonce'],
        )

        return Block(
            size=rpc_block['size'],
            header=header,
            tx=rpc_block['tx'],
            nextblockhash=rpc_block['nextblockhash'],
            height=rpc_block['height'],
            chainwork=int(rpc_block['chainwork'], 16),
        )


class TransactionFactory(object):
    @staticmethod
    def from_stream(stream, coinbase=False):
        tr_start = stream.tell()

        # A version number to track software/protocol upgrades
        version = uint4(stream)

        # Number of inputs in this ParsedTransaction
        vin_count = varint(stream)

        skip = 0
        # Parse the coinbase input
        if coinbase:
            vin = [VinFactory.from_stream(stream, coinbase=True)]
            skip = 1
        else:
            vin = []

        # Parse other inputs (if they exist)
        for i in range(skip, vin_count):
            vin.append(VinFactory.from_stream(stream))

        # Number of outputs in this transction
        vout_count = varint(stream)

        # Parse the ParsedTransaction outputs
        vout = [VoutFactory.from_stream(stream) for i in range(0, vout_count)]

        # ParsedTransaction locktime
        locktime = uint4(stream)

        tr_end = stream.tell()

        # rewind so we can calculate the txid
        # OPTIMIZE: use io.BytesIO to pass bytes as a stream
        stream.seek(tr_start)
        tr_bytes = stream.read(tr_end - tr_start)
        txid = double_sha(tr_bytes, reverse=True)

        total = round(sum([v.value for v in vout]), 8)

        return Transaction(
            version=version,
            vin=vin,
            vout=vout,
            locktime=locktime,
            txid=txid,
            total=total
        )


class VinFactory(object):
    @staticmethod
    def from_stream(stream, coinbase=False):
        if not coinbase:
            prev_txid = hash32(stream)
            vout_index = uint4(stream)
            script_len = varint(stream)
            script_hex = binascii.hexlify(stream.read(script_len))
            sequence = uint4(stream)

            return Vin(
                prev_txid=prev_txid,
                vout_index=vout_index,
                hex=script_hex,
                sequence=sequence,
            )
        else:
            # Throw away these values for coinbase ParsedTransactions
            _ = (hash32(stream), uint4(stream))

            script_len = varint(stream)
            coinbase = binascii.hexlify(stream.read(script_len))
            sequence = uint4(stream)

            return Vin(
                coinbase=coinbase,
                sequence=sequence
            )


class VoutFactory(object):
    @staticmethod
    def parse_script(script):
        """
        Parses the bitcoin script - https://en.bitcoin.it/wiki/Script,
        currently supports only pay2pubkey and pay2pubkeyhash ParsedTransactions
        """
        if script[:4] == ScriptOperator.OP_DUP.value + ScriptOperator.OP_HASH160.value:
            # Pay to public key hash ParsedTransaction
            (pubkey, address) = VoutFactory.parse_pay2pubkey_hash(script)
            return {
                "asm": "OP_DUP OP_HASH160 %s OP_EQUALVERIFY OP_CHECKSIG" % pubkey,
                "reqSigs": 1,
                "type": "pubkeyhash",
                "addresses": [address]
            }
        elif script[-2:] == ScriptOperator.OP_CHECKSIG.value:
            # Pay to public key ParsedTransaction (deprecated)
            (pubkey, address) = VoutFactory.parse_pay2pubkey(script)
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
            (pubkey, address) = VoutFactory.parse_pay2scripthash(script)
            return {
                "asm": "OP_HASH160 %s OP_EQUAL" % pubkey,
                "reqSigs": 1,
                "type": "scripthash",
                "addresses": [address]
            }
        else:
            raise Exception("[PARSE_SCRIPT] Unknown script format: %s" % script)

    @staticmethod
    def parse_pay2pubkey(script):
        # First 2 bytes is num bytes to be pushed to the stack
        # Last 2 are OP_CHECKSIG, pubkey is in the middle
        pubkey = script[2:-2]

        # Create address from public key (HASH160 + B58_CHECK)
        address = pubkey_to_address(pubkey, magicbyte=GAME_MAGIC_BYTE)

        return (pubkey, address)

    @staticmethod
    def parse_pay2pubkey_hash(script):
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

    @staticmethod
    def parse_pay2scripthash(script):
        # First 2 bytes is OP_HASH160
        # Second 2 bytes is num bytes to be pushed to the stack
        # Then comes the pubkey
        pubkey = script[4:-2]

        # P2SH addresses use the version prefix 5, which results in
        # Base58Check-encoded addresses that start with a 3
        address = bin_to_b58check(binascii.unhexlify(pubkey), PAY_TO_SCRIPT_MAGIC_BYTE)

        return (pubkey, address)

    @staticmethod
    def from_stream(stream):
        # Value in satoshi, convert it to GAME
        value = uint8(stream) * 10e-9

        # Length of the script after this in bytes
        script_len = varint(stream)

        # Read script of length script_len
        # REMEMBER: use binascii not the custom bin_to_hex function
        # because bin_to_hex ignored zeroes for some reason
        script_hex = binascii.hexlify(stream.read(script_len))

        # Parse the script to extract addresses
        parsed = VoutFactory.parse_script(script_hex)

        asm = parsed.get("asm")
        addresses = parsed.get("addresses")
        script_type = parsed.get("type")
        reqSigs = parsed.get("reqSigs")

        return Vout(
            value=value,
            hex=script_hex,
            asm=asm,
            addresses=addresses,
            type=script_type,
            reqSigs=reqSigs
        )