import connexion
from gateways import DatabaseGateway
from pymongo import MongoClient
from serializers import TransactionSerializer, BlockSerializer
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"


mongo = MongoClient()
db = DatabaseGateway(database=mongo.exploder)
rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                       % (RPC_USER, RPC_PASSWORD))


############
#  BLOCKS  #
############
def get_latest_blocks(limit, offset):
    import pdb
    pdb.set_trace()
    blocks = db.get_latest_blocks(limit, offset)
    return [BlockSerializer.to_web(block) for block in blocks]


def get_block_by_hash(block_hash):
    try:
        return BlockSerializer.to_web(db.get_block_by_hash(block_hash))
    except KeyError:
        return "Block with given hash doesn't exist", 404


def get_block_by_height(height):
    try:
        return BlockSerializer.to_web(db.get_block_by_height(height))
    except KeyError:
        return "Block with given height doesn't exist", 404


def get_block_confirmations(block_hash):
    try:
        block = db.get_block_by_hash(block_hash)
    except KeyError:
        return "Block with given hash doesn't exist", 404

    return db.calculcate_block_confirmations(block)


##################
#  TRANSACTIONS  #
##################
def get_transaction_by_txid(txid):
    try:
        return TransactionSerializer.to_web(db.get_transaction(txid))
    except KeyError:
        return "Transaction with given ID not found", 404


def get_transaction_confirmations(txid):
    try:
        tr = db.get_transaction_by_txid(txid)
    except KeyError:
        return "Transaction with given txid not found", 404

    block = db.get_block_by_hash(tr['blockhash'])

    return db.calculate_block_confirmations(block)


def get_latest_transactions(limit, offset):
    transactions = db.get_latest_transactions(limit, offset)
    return [TransactionSerializer.to_web(tr) for tr in transactions]


def get_transactions_by_blockhash(blockhash):
    try:
        return [TransactionSerializer.to_web(tr) for tr in db.get_transactions_by_blockhash(blockhash)]
    except KeyError:
        return []


###############
#  ADDRESSES  #
###############
def get_address(address_hash):
    pass


def get_address_unspent(address_hash):
    pass


#############
#  NETWORK  #
#############
def send_raw_transaction(hex):
    try:
        rpc.sendrawtransaction(hex)
    except JSONRPCException as e:
        return e.error, 400


api = connexion.App(__name__)
api.add_api('explorer_api.yaml')
api.run(server='tornado', port=5000)