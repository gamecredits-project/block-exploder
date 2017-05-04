import connexion
import sys
import os
import ConfigParser
from gateways import DatabaseGateway
from pymongo import MongoClient
from serializers import TransactionSerializer, BlockSerializer, VoutSerializer
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

rpc_user = config.get('syncer', 'rpc_user')
rpc_password = config.get('syncer', 'rpc_password')
rpc_port = config.getint('syncer', 'rpc_port')

mongo = MongoClient()
db = DatabaseGateway(database=mongo.exploder, config=config)
rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:%s"
                       % (rpc_user, rpc_password, rpc_port))


############
#  BLOCKS  #
############
def get_latest_blocks(limit, offset):
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
    trs, volume = db.get_address_statistics(address_hash)
    transactions = [TransactionSerializer.to_web(tr) for tr in trs]
    return {
        "address": address_hash,
        "volume": volume,
        "transactions": transactions,
    }


def get_address_unspent(address_hash):
    vouts = db.get_address_unspent(address_hash)
    unspent = [VoutSerializer.to_web(vout) for vout in vouts]
    balance = sum([vout["value"] for vout in unspent])
    return {
        "address": address_hash,
        "balance": balance,
        "unspent": unspent
    }


#############
#  NETWORK  #
#############
def send_raw_transaction(hex):
    try:
        rpc.sendrawtransaction(hex)
    except JSONRPCException as e:
        return e.error, 400


def create_and_run_app(port=5000):
    api = connexion.App(__name__)
    api.add_api('explorer_api.yaml')
    api.run(server='tornado', port=port)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: python api.py [PORT]")
        sys.exit(1)

    create_and_run_app(int(sys.argv[1]))
