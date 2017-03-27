class Block(object):
    def __init__(self, **kwargs):
        # Size of this block in bytes
        self.size = kwargs.get('size')

        # Block header
        header = kwargs.get('header')

        # Unpack the header - shorthand for writing bunch of assignments liked
        # self.hash = header.hash
        if header:
            for (key, val) in header.__dict__.iteritems():
                setattr(self, key, val)

        # List of block transactions
        self.tx = kwargs.get('tx')

        # Information about the blocks position
        # in a dat file: {
        #  "index": <index of dat file>
        #  "start": <block start byte>
        #  "end": <block end byte>
        # }
        # None if block is loaded from RPC
        self.dat = kwargs.get('dat')

        self.nextblockhash = kwargs.get('nextblockhash')

        self.height = kwargs.get('height')

        # Cumulative amount of work done to get to this block
        # Used to determine the best chain
        self.chainwork = kwargs.get('chainwork')

        # Index of the chain this block belongs to
        # (main chain or sidechain)
        self.chain = kwargs.get('chain')

        # Total amount in all transactions
        self.total = kwargs.get('total')

    def to_mongo(self):
        return {
            "hash": self.hash,
            "size": self.size,
            "height": self.height,
            "version": self.version,
            "merkleroot": self.merkleroot,
            "tx": self.tx,
            "time": self.time,
            "nonce": self.nonce,
            "bits": self.bits,
            "difficulty": self.difficulty,
            "chainwork": hex(self.chainwork),
            "previousblockhash": self.previousblockhash,
            "nextblockhash": self.nextblockhash,
            "target": hex(self.target),
            "dat": self.dat,
            "total": self.total,
            "work": self.work,
            "chain": self.chain
        }


class BlockHeader(object):
    def __init__(self, **kwargs):
        # Block hash (unique identifier)
        self.hash = kwargs.get('hash')

        # A version number to track software/protocol upgrades
        self.version = kwargs.get('version')

        # A reference to the hash of the previous (parent) block in the chain
        self.previousblockhash = kwargs.get('previousblockhash')

        # A hash of the root of the merkle tree of this blocks ParsedTransactions
        self.merkleroot = kwargs.get('merkleroot')

        # The approximate creation time of this block (seconds from Unix Epoch)
        self.time = kwargs.get('time')

        # Difficulty bits in hexadeximal format
        # This notation expresses the difficulty target as a coefficient/exponent format,
        # with the first two hexadecimal digits for the exponent
        # and the rest as the coefficient.
        self.bits = kwargs.get('bits')

        # Calculate target, formula from Mastering Bitcoin book
        self.target = kwargs.get('target')

        # Difficulty is calculated as a ratio between the maximum allowed difficulty
        # and the blocks difficulty target
        self.difficulty = kwargs.get('difficulty')

        # A counter used for the proof-of-work algorithm
        self.nonce = kwargs.get('nonce')

        # Block work
        self.work = kwargs.get('work')


class Transaction(object):
    def __init__(self, **kwargs):
        # A version number to track software/protocol upgrades
        self.version = kwargs.get('version')

        # Transaction inputs
        self.vin = kwargs.get('vin')

        # Transaction outputs
        self.vout = kwargs.get('vout')

        self.locktime = kwargs.get('locktime')

        # Transaction hash (unique identifier)
        self.txid = kwargs.get('txid')

        # Total value of all outputs
        self.total = kwargs.get('total')

    def to_mongo(self):
        formatted = {
            "version": self.version,
            "locktime": self.locktime,
            "txid": self.txid,
            "vin": [],
            "vout": [],
            "total": self.total
        }

        for v in self.vin:
            formatted['vin'].append({
                "prev_txid": v.prev_txid,
                "vout_index": v.vout_index,
                "coinbase": v.coinbase
            })

        for v in self.vout:
            formatted['vout'].append({
                "addresses": v.addresses,
                "type": v.type,
                "value": v.value
            })

        return formatted


class Vin(object):
    def __init__(self, **kwargs):
        self.prev_txid = kwargs.get('prev_txid')
        self.vout_index = kwargs.get('vout_index')
        self.hex = kwargs.get('hex')
        self.sequence = kwargs.get('sequence')
        self.coinbase = kwargs.get('coinbase')

    def to_mongo(self, spender_txid):
        return {
            "txid": spender_txid,
            "prev_txid": self.prev_txid,
            "vout_index": self.vout_index,
            "hex": self.hex,
            "sequence": self.sequence,
            "coinbase": self.coinbase
        }


class Vout(object):
    def __init__(self, **kwargs):
        self.value = kwargs.get('value')
        self.hex = kwargs.get('hex')
        self.asm = kwargs.get('asm')
        self.addresses = kwargs.get('addresses')
        self.type = kwargs.get('type')
        self.reqSigs = kwargs.get('reqSigs')

    def to_mongo(self, spender_txid, index):
        formatted = []

        if self.addresses:
            for adr in self.addresses:
                formatted.append({
                    "txid": spender_txid,
                    "index": index,
                    "value": self.value,
                    "asm": self.asm,
                    "address": adr,
                    "type": self.type,
                    "reqSigs": self.reqSigs
                })
        else:
            formatted = [{
                "txid": spender_txid,
                "index": index,
                "value": self.value,
                "asm": self.asm,
                "address": None,
                "type": self.type,
                "reqSigs": self.reqSigs
            }]

        return formatted
