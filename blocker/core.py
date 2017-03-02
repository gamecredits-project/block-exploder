from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from datetime import datetime
import subprocess
import copy
from pymongo import MongoClient
import humanize

DATABASE_DIRECTORY = "/home/vagrant/.blocker"
DATADIR_PATH = "/home/vagrant/.gamecredits"
RPC_USER = "vagrant"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"


def du(path):
    """disk usage in human readable format (e.g. '2,1GB')"""
    return subprocess.check_output(['du', '-sh', path]).split()[0].decode('utf-8')


class Block(object):
    def __init__(self, block_dict):
        # Hash details
        self.hash = block_dict['hash']
        self.chainwork = block_dict['chainwork']
        self.nonce = block_dict['nonce']
        self.merkleroot = block_dict['merkleroot']

        # Links
        # TODO: write it like this
        # self.nexblockhash = block_dict.get('nextblockhash')
        if 'nextblockhash' in block_dict:
            self.nextblockhash = block_dict['nextblockhash']
        else:
            self.nextblockhash = None

        if 'previousblockhash' in block_dict:
            self.previousblockhash = block_dict['previousblockhash']
        else:
            self.previousblockhash = None

        if "num_transactions" in block_dict:
            self.num_transactions = block_dict['num_transactions']
        elif "tx" in block_dict:
            self.num_transactions = len(block_dict["tx"])
        else:
            self.num_transactions = 0

        # Block details
        self.height = block_dict['height']
        self.time = block_dict['time']

        self.difficulty = str(block_dict['difficulty'])
        self.version = block_dict['version']
        self.bits = block_dict['bits']
        self.size = block_dict['size']

        if "total" in block_dict:
            self.total = block_dict["total"]
        else:
            self.total = 0

    def serialize(self):
        return self.__dict__

    def update_nextblockhash(self, nextblockhash, db):
        self.nextblockhash = nextblockhash

        db.find_one_and_update({"height": self.height}, {"$set": {"nextblockhash": self.nextblockhash}})

    def __repr__(self):
        return "<Block: height: %s, hash: %s, time: %s, total: %s>" \
            % (self.height, self.hash, self.time, self.total)


class Transaction(object):
    def __init__(self, tr_dict):
        if "blockhash" in tr_dict:
            self.blockhash = tr_dict['blockhash']
        else:
            self.blockhash = None

        self.hex = tr_dict['hex']

        self.txid = tr_dict['txid']

        if "time" in tr_dict:
            self.time = tr_dict['time']
        else:
            self.time = None

        if "blocktime" in tr_dict:
            self.blocktime = tr_dict['blocktime']
        else:
            self.blocktime = None

        self.vin = []
        for tr_in in tr_dict['vin']:
            if "txid" in tr_in:
                self.vin.append(TransactionInput(tr_in))

        self.vout = []
        for tr_out in tr_dict['vout']:
            self.vout.append(TransactionOutput(tr_out))

        if "total" in tr_dict:
            self.total = tr_dict["total"]
        else:
            self.total = sum([float(out.value) for out in self.vout])

    def __repr__(self):
        return "<Transaction: txid: %s, inputs:%s, outputs: %s, total: %s>" \
            % (self.txid, self.inputs, str(self.outputs), self.total)

    def serialize(self):
        formatted = copy.deepcopy(self.__dict__)
        formatted['vout'] = [vout.serialize() for vout in self.vout]
        formatted['vin'] = [vin.serialize() for vin in self.vin]
        return formatted


class TransactionInput(object):
    def __init__(self, tr_dict):
        self.txid = tr_dict['txid']

    def __repr__(self):
        return "<TransactionInput: %s>" % self.txid

    def serialize(self):
        return {
            "txid": self.txid
        }


class TransactionOutput(object):
    def __init__(self, tr_dict):
        self.value = str(tr_dict["value"])

        self.addresses = []

        if "scriptPubKey" in tr_dict:
            if "addresses" in tr_dict["scriptPubKey"]:
                self.addresses = tr_dict["scriptPubKey"]["addresses"][:]
        elif "addresses" in tr_dict:
            self.addresses = tr_dict["addresses"][:]

    def __repr__(self):
        return "<TransactionOutput: addresses: %s, amount: %s>" \
            % (self.addresses, self.value)

    def serialize(self):
        return {
            "value": self.value,
            "addresses": self.addresses
        }


class Address(object):
    def __init__(self, address, transactions=[]):
        self.address = address
        self.transactions = transactions
        self.total = sum([float(tr.total) for tr in self.transactions])


class AddressTransaction(object):
    def __init__(self, addr_tr_dict):
        self.address = addr_tr_dict['address']
        self.txid = addr_tr_dict['txid']
        self.value = addr_tr_dict['value']

    def serialize(self):
        return self.__dict__


class Blockchain(object):
    @property
    def height(self):
        highest_block = self._get_highest_block()

        if highest_block:
            return int(highest_block.height)
        else:
            return 0

    @height.setter
    def height(self, value):
        pass

    def _get_highest_block(self):
        return Block(self.blocks.find_one(sort=[("height", -1)]))

    def __init__(self, rpc_user, rpc_password, datadir_path=DATADIR_PATH):
        self.mongo = MongoClient()

        self.exploder_db = self.mongo.exploder

        self.blocks = self.exploder_db.blocks
        self.transactions = self.exploder_db.transactions
        self.addresses = self.exploder_db.addresses

        self.datadir_path = datadir_path

        # RPC_USER and RPC_PASSWORD are set in the bitcoin.conf file
        self.rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                                    % (rpc_user, rpc_password))

    def sync(self, limit=None):
        """
        Syncs the database with the blockchain.

        @return: the number of synced blocks
        """
        block_count = self.rpc.getblockcount()
        highest_known = self.height

        blocks = []
        addresses = []
        transactions = []

        # If the db is up to date there's nothing to sync
        if not (highest_known < block_count):
            return 0

        print("[%s] Sync started. Last synced block: %s, blockchain height: %s"
              % (datetime.now(), highest_known, block_count))

        # If the db is multiple blocks behind the blockchain
        # start the sync in bulk mode, for better performance
        bulk_insert = False
        if block_count - highest_known > 1:
            print("[BULK] Behind %s blocks. Starting bulk sync." % (block_count - highest_known))
            bulk_insert = True

        for i in xrange(highest_known + 1, block_count + 1):
            # Check if sync has reached the (user provided) limit
            if limit and i > highest_known + limit:
                print("[LIMIT] Synced %s blocks")
                break

            # Initialize the i-th Block
            blockhash = self.rpc.getblockhash(i)
            block_dict = self.rpc.getblock(blockhash)
            block = Block(block_dict)

            # In the first iteration: check if the current last known block
            # doesn't have nextblockhash, and set it if needed
            if i == highest_known + 1:
                last_known_block = self._get_highest_block()

                if last_known_block and not last_known_block.nextblockhash:
                    last_known_block.update_nextblockhash(block.hash, self.blocks)

            # This list holds all of the transactions for the current block
            block_transactions = []
            for txid in block_dict['tx']:
                try:
                    # Initialize the transaction
                    tr_dict = self.rpc.getrawtransaction(txid, 1)
                    transaction = Transaction(tr_dict)
                    block_transactions.append(transaction)

                    # If not in bulk insert mode
                    # write it to the db immediately
                    if not bulk_insert:
                        self.put_transaction(transaction)

                    for output in transaction.vout:
                        for address in output.addresses:
                            address_object = AddressTransaction({
                                "address": address,
                                "txid": transaction.txid,
                                "value": output.value
                            })

                            if bulk_insert:
                                addresses.append(address_object)
                            else:
                                self.put_address(address_object)

                except JSONRPCException as er:
                    print er.error

            if bulk_insert:
                transactions += block_transactions

            block.total = sum([float(tr.total) for tr in block_transactions])

            if bulk_insert:
                blocks.append(block)
            else:
                self.put_block(block)

            if bulk_insert and i % 500 == 0:
                if addresses:
                    self.put_many_addresses(addresses)

                if transactions:
                    self.put_many_transactions(transactions)

                if blocks:
                    self.put_many_blocks(blocks)

                progress = float(i * 100) / block_count
                print("Indexed %s out of %s blocks. Progress: %s%%"
                      % (i, block_count, progress))
                blocks = []
                addresses = []
                transactions = []

        # Finalize bulk insert
        if bulk_insert:
            if addresses:
                self.put_many_addresses(addresses)

            if transactions:
                self.put_many_transactions(transactions)

            if blocks:
                self.put_many_blocks(blocks)

        print("[%s] Sync complete." % datetime.now())
        return i - highest_known

    ################################
    # TRANSACTION
    ################################
    def get_transaction(self, tr_hash):
        transaction_dict = self.transactions.find_one({"txid": tr_hash})

        if not transaction_dict:
            try:
                transaction = Transaction(self.rpc.getrawtransaction(tr_hash, 1))
                return transaction
            except JSONRPCException:
                pass
        else:
            transaction = Transaction(transaction_dict)
            return transaction

        return None

    def put_transaction(self, transaction):
        self.transactions.insert_one(transaction.serialize())

    def put_many_transactions(self, tr_list):
        dict_array = []
        for tr in tr_list:
            dict_array.append(tr.serialize())

        self.transactions.insert_many(dict_array)

    def calculate_transaction_confirmations(self, transaction):
        if not transaction.blockhash:
            return 0

        transaction_block = self.get_block(transaction.blockhash)

        if not transaction_block:
            return 0

        return self.calculate_block_confirmations(transaction_block)

    def get_latest_transactions(self, num):
        mempool = self.rpc.getrawmempool()
        transactions = [Transaction(self.rpc.getrawtransaction(txid, 1)) for txid in mempool]

        if len(transactions) < num:
            latest = self.transactions.find(sort=[("time", -1)])\
                .limit(num - len(transactions))

            latest = [Transaction(tr) for tr in latest]
            transactions += latest

        return transactions[:num]

    ################################
    # BLOCK
    ################################
    def get_block(self, block_query):
        block_dict = self._get_block_by_hash(block_query) or self._get_block_by_index(block_query)

        if block_dict:
            block = Block(block_dict)
            return block
        else:
            return None

    def _get_block_by_hash(self, block_hash):
        return self.blocks.find_one({"hash": block_hash})

    def _get_block_by_index(self, block_index):
        try:
            block_index = int(block_index)
        except ValueError:
            return None

        return self.blocks.find_one({"height": block_index})

    def put_block(self, block):
        self.blocks.insert_one(block.serialize())

    def put_many_blocks(self, block_list):
        dict_array = []
        for block in block_list:
            dict_array.append(block.serialize())

        self.blocks.insert_many(dict_array)

    def get_latest_blocks(self, num, offset=0):
        return [Block(block_dict) for block_dict in self.blocks.find(sort=[("height", -1)]).skip(offset).limit(num)]

    def calculate_block_confirmations(self, block):
        return self.height - block.height

    def get_block_transactions(self, block):
        return [
            Transaction(tr_dict) for tr_dict in self.transactions.find({"blockhash": block.hash})
        ]

    ################################
    # ADDRESS
    ################################
    def get_address(self, address_query):
        address_list = self.addresses.find({"address": address_query})

        if address_list:
            txids = [tup["txid"] for tup in address_list]
            if len(txids) > 20:
                txids = txids[:20]
            transactions = [self.get_transaction(txid) for txid in txids]
            return Address(address_query, transactions)
        else:
            return None

    def put_address(self, address):
        self.addresses.insert_one(address.serialize())

    def put_many_addresses(self, address_list):
        dict_array = []
        for address in address_list:
            dict_array.append(address.serialize())

        self.addresses.insert_many(dict_array)

    def get_disk_usages(self):
        return {
            'blockchain_size': du(self.datadir_path),
            'database_size': humanize.naturalsize(self.exploder_db.command("dbstats")['dataSize']),
        }

    def get_status(self):
        client_info = self.rpc.getinfo()
        client_info['balance'] = str(client_info['balance'])
        client_info['difficulty'] = str(client_info['difficulty'])
        client_info['paytxfee'] = str(client_info['paytxfee'])
        client_info['relayfee'] = str(client_info['relayfee'])

        return {
            'height': self.height,
            'client': client_info
        }
