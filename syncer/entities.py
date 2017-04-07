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

        # Information about the blocks position in a dat file:
        # {
        #  "index": <index of dat file>
        #  "start": <block start byte>
        #  "end": <block end byte>
        # }
        self.dat = kwargs.get('dat')

        # Hash of the next block in the chain
        self.nextblockhash = kwargs.get('nextblockhash')

        # Position of the block in the chain
        self.height = kwargs.get('height')

        # Cumulative amount of work done to get to this block
        # Used to determine the best chain
        self.chainwork = kwargs.get('chainwork')

        # Index of the chain this block belongs to
        # (main chain or sidechain)
        self.chain = kwargs.get('chain')

        # Total amount in all transactions
        self.total = kwargs.get('total')

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.hash == other.hash and self.previousblockhash == other.previousblockhash \
                and self.height == other.height
        return False

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)


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

    def __eq__(self, other):
        """Override the default Equals behavior"""
        if isinstance(other, self.__class__):
            return self.hash == other.hash and self.previousblockhash == other.previousblockhash
        return False

    def __ne__(self, other):
        """Define a non-equality test"""
        return not self.__eq__(other)


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

        # Hash of the block this transaction belongs to
        self.blockhash = kwargs.get('blockhash')

        # Block mined time
        self.blocktime = kwargs.get('blocktime')


class Vin(object):
    def __init__(self, **kwargs):
        # Identifier of the parent transaction
        self.txid = kwargs.get('txid')

        # Identifier of the tr that holds the output to be spent
        self.prev_txid = kwargs.get('prev_txid')

        # Position of the output in previous transaction
        self.vout_index = kwargs.get('vout_index')

        # Spending script in hexadecimal format
        self.hex = kwargs.get('hex')

        # Sequence number
        self.sequence = kwargs.get('sequence')

        # Coinbase hex for generation transactions
        self.coinbase = kwargs.get('coinbase')


class Vout(object):
    def __init__(self, **kwargs):
        self.value = kwargs.get('value')
        self.hex = kwargs.get('hex')
        self.asm = kwargs.get('asm')
        self.addresses = kwargs.get('addresses')
        self.type = kwargs.get('type')
        self.reqSigs = kwargs.get('reqSigs')
        self.txid = kwargs.get('txid')
        self.index = kwargs.get('index')

