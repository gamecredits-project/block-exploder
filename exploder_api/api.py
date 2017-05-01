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


def get_latest_blocks(limit, offset):
    blocks = db.get_latest_blocks(limit, offset)
    return [BlockSerializer.to_web(block) for block in blocks]


def get_block_by_hash(block_hash):
    try:
        return BlockSerializer.to_web(db.get_block_by_hash(block_hash))
    except KeyError:
        return "Block with given hash doesn't exist", 404


def get_address_unspent(address):
    try:
        return [VoutSerializer.to_web(vout) for vout in db.get_address_unspent(address)]
    except KeyError:
        return []


def get_transaction_by_txid(txid):
    try:
        return TransactionSerializer.to_web(db.get_transaction(txid))
    except KeyError:
        return "Transaction with given ID not found", 404


def get_transactions(blockhash=None, address=None):
    try:
        if blockhash:
            return [TransactionSerializer.to_web(tr) for tr in db.get_block_transactions(blockhash)]
        elif address:
            return [TransactionSerializer.to_web(tr) for tr in db.get_transactions_by_address(address)]
        else:
            return "Provide either blockhash or address", 400
    except KeyError:
        return []


def send_raw_transaction(hex):
    try:
        rpc.sendrawtransaction(hex)
    except JSONRPCException as e:
        return e.error, 400


api = connexion.App(__name__)
api.add_api('explorer_api.yaml')
api.run(server='tornado', port=5000)
