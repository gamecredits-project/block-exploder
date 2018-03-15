import connexion
import sys
import os
import ConfigParser
from flask_cors import CORS
from gateways import DatabaseGateway
from pymongo import MongoClient
from serializers import TransactionSerializer, BlockSerializer, HashrateSerializer, \
    NetworkStatsSerializer, SyncHistorySerializer, ClientInfoSerializer, PriceSerializer, \
    SearchSerializer, TransactoinCountSerializer, VolumeSerializer, \
    BalanceSerializer, UnspentTransactionSerializer, AddressSerializer, PriceHistorySerializer, \
    PriceStatsSerializer, VolumesSerializer

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from helpers import validate_address, validate_sha256_hash, check_if_address_post_key_is_valid

######################
#  INITIALIZE STUFF  #
######################
CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)

rpc_user = config.get('syncer', 'rpc_user')
rpc_password = config.get('syncer', 'rpc_password')
rpc_port = config.getint('syncer', 'rpc_port')
mongo_user = config.get('syncer', 'mongo_user')
mongo_pass = config.get('syncer', 'mongo_pass')


mongo = MongoClient('127.0.0.1', 
                    username=mongo_user,
                    password=mongo_pass)
                    
db = DatabaseGateway(database=mongo.exploder, config=config)
rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:%s"
                       % (rpc_user, rpc_password, rpc_port))


############
#  BLOCKS  #
############
def get_latest_blocks(limit, offset):
    if not isinstance(offset, int):
        return "Offset too large", 400
    blocks = db.get_latest_blocks(limit, offset)
    return [BlockSerializer.to_web(block) for block in blocks]


def get_block_by_hash(block_hash):
    if not validate_sha256_hash(block_hash):
        return "Invalid block hash", 400
    try:
        return BlockSerializer.to_web(db.get_block_by_hash(block_hash))
    except KeyError:
        return "Block with given hash doesn't exist", 404


def get_block_by_height(height):
    # If we don't check whether height is integer
    # MongoDB will throw OverflowError
    # because MongoDB can only handle up to 8-byte ints
    if not isinstance(height, int):
        return "Block height too large", 400
    try:
        return BlockSerializer.to_web(db.get_block_by_height(height))
    except KeyError:
        return "Block with given height doesn't exist", 404


def get_block_confirmations(block_hash):
    if not validate_sha256_hash(block_hash):
        return "Invalid block hash", 400
    try:
        block = db.get_block_by_hash(block_hash)
    except KeyError:
        return "Block with given hash doesn't exist", 404

    return {
        "hash": block_hash,
        "confirmations": db.calculate_block_confirmations(block, rpc)
    }


##################
#  TRANSACTIONS  #
##################
def get_transaction_by_txid(txid):
    if not validate_sha256_hash(txid):
        return "Invalid transaction ID", 400
    try:
        return TransactionSerializer.to_web(db.get_transaction_by_txid(txid, rpc))
    except KeyError:
        return "Transaction with given ID not found", 404


def get_transaction_confirmations(txid):
    if not validate_sha256_hash(txid):
        return "Invalid transaction ID", 400
    try:
        tr = db.get_transaction_by_txid(txid, rpc)
    except KeyError:
        return "Transaction with given txid not found", 404

    block = db.get_block_by_hash(tr['blockhash'])

    return {
        "txid": txid,
        "confirmations": db.calculate_block_confirmations(block, rpc)
    }


def get_latest_transactions(limit, offset):
    if not isinstance(offset, int):
        return "Offset too large", 400
    transactions = db.get_latest_transactions(limit, offset)
    return [TransactionSerializer.to_web(tr) for tr in transactions]


def get_transactions_by_blockhash(blockhash):
    if not validate_sha256_hash(blockhash):
        return "Invalid block hash", 400
    try:
        return [TransactionSerializer.to_web(tr) for tr in db.get_transactions_by_blockhash(blockhash)]
    except KeyError:
        return []


###############
#  ADDRESSES  #
###############
def get_address_transactions(address_hash, start=None):
    if start and (not isinstance(start, int)):
        return "Start too large", 400
    if not validate_address(address_hash):
        return "Invalid address hash", 400
    trs = db.get_address_transactions(address_hash, start, limit=50)

    if len(trs) == 50:
        last_transaction = trs[len(trs) - 1]
        return {
            "transactions": [TransactionSerializer.to_web(tr) for tr in trs],
            "next": "/addresses/%s?start=%s" % (address_hash, last_transaction['blocktime'])
        }
    else:
        return {
            "transactions": [TransactionSerializer.to_web(tr) for tr in trs],
            "next": None
        }

def post_addresses_transactions(addresses_hash):
    # Start must be declared None, in case that start doesn't
    # exist in the post body
    start = None

    if not check_if_address_post_key_is_valid(addresses_hash):
        return "Bad post request", 400

    addresses_hash_no_json = addresses_hash['addresses']

    for address_hash in addresses_hash_no_json:
        if not validate_address(address_hash):
            return "Invalid address hash", 400

    if 'start' in addresses_hash:
        start = addresses_hash['start']
        if start and(not isinstance(start, int)):
            return "Start too large", 400

    trs = db.post_addresses_transactions(addresses_hash_no_json, start, limit=50)


    if len(trs) == 50:
        last_transaction = trs[len(trs) - 1]
        return {
            "transactions": [TransactionSerializer.to_web(tr) for tr in trs],
            "next": last_transaction['blocktime']
        }
    else:
        return {
            "transactions": [TransactionSerializer.to_web(tr) for tr in trs],
            "next": None
        }


def get_address_num_transactions(address_hash):
    if not validate_address(address_hash):
        return "Invalid address hash", 400
    tr_count = db.get_address_num_transactions(address_hash)
    return TransactoinCountSerializer.to_web(address_hash, tr_count)

def post_addresses_num_transactions(addresses_hash):

    if not check_if_address_post_key_is_valid(addresses_hash):
        return "Bad post request", 400

    addresses_hash_no_json = addresses_hash['addresses']
    for address_hash in addresses_hash_no_json:
        if not validate_address(address_hash):
            return "Invalid address hash", 400

    tr_count = db.post_addresses_num_transactions(addresses_hash_no_json)
    return TransactoinCountSerializer.to_web(addresses_hash_no_json, tr_count)


def get_address_volume(address_hash):
    if not validate_address(address_hash):
        return "Invalid address hash", 400
    volume = db.get_address_volume(address_hash)
    return VolumeSerializer.to_web(address_hash, volume)

def post_addresses_volume(addresses_hash):

    if not check_if_address_post_key_is_valid(addresses_hash):
        return "Bad post request", 400

    addresses_hash_no_json = addresses_hash['addresses']

    for address_hash in addresses_hash_no_json:
        if not validate_address(address_hash):
            return "Invalid address hash", 400

    volumes, total_volume = db.post_addresses_volume(addresses_hash_no_json)

    return VolumesSerializer.to_web(addresses_hash_no_json, total_volume, volumes)


def get_address_unspent(address_hash, start=None):
    if not validate_address(address_hash):
        return "Invalid address hash", 400
    if start and (not isinstance(start, int)):
        return "Start too large", 400

    unspent = db.get_address_unspent(address_hash, start, limit=50)
    if unspent:
        unspent_transaction_address = unspent[0]['vout']['addresses'][0]
    else:
        unspent_transaction_address = unspent

    if len(unspent) == 50:
        last_unspent_transaction = unspent[len(unspent)-1]
        return {
            "next": "/addresses/%s/unspent?start=%s" %
                    (address_hash, last_unspent_transaction['blocktime']),
            "address": unspent_transaction_address,
            "utxo": [UnspentTransactionSerializer.to_web(tr) for tr in unspent]
        }

    return {
        "address": unspent_transaction_address,
        "utxo": [UnspentTransactionSerializer.to_web(tr) for tr in unspent],
        "next" : None
    }

def post_addresses_unspent(addresses_hash):
    start = None

    if not check_if_address_post_key_is_valid(addresses_hash):
        return "Bad post request", 400

    addresses_hash_no_json = addresses_hash['addresses']
    if 'start' in addresses_hash:
        start = addresses_hash['start']
        if start and (not isinstance(start, int)):
            return "Start too large", 400

    for address_hash in addresses_hash_no_json:
        if not validate_address(address_hash):
            return "Invalid address hash", 400

    unspent = db.post_addresses_unspent(addresses_hash_no_json, start, limit=50)

    if len(unspent) == 50:
        last_unspent_transaction = unspent[len(unspent)-1]

        return {
            "next": last_unspent_transaction['blocktime'],
            "addresses": addresses_hash['addresses'],
            "utxo": [UnspentTransactionSerializer.to_web(tr) for tr in unspent]
        }

    return {
        "addresses": addresses_hash_no_json,
        "utxo": [UnspentTransactionSerializer.to_web(tr) for tr in unspent],
        "next": None
    }


def get_address_balance(address_hash):
    if not validate_address(address_hash):
        return "Invalid address hash", 400
    balance = db.get_address_balance(address_hash)
    return BalanceSerializer.to_web(address_hash, balance)

def post_addresses_balance(addresses_hash):
    if not check_if_address_post_key_is_valid(addresses_hash):
        return "Bad post request", 400

    addresses_hash_no_json = addresses_hash['addresses']

    for address_hash in addresses_hash_no_json:
        if not validate_address(address_hash):
            return "Invalid address hash", 400

    balance = db.post_addresses_balance(addresses_hash_no_json)
    return BalanceSerializer.to_web(addresses_hash_no_json, balance)

#############
#  NETWORK  #
#############
def send_raw_transaction(hex):
    try:
        rpc.sendrawtransaction(hex)
    except JSONRPCException as e:
        return e.error, 400


def get_latest_hashrates(limit):
    hash_rates = db.get_latest_hashrates(limit)
    return [HashrateSerializer.to_web(hash_rate) for hash_rate in hash_rates]


def get_network_stats():
    hash_rate = db.get_latest_hashrates(limit=1)
    stats = db.get_network_stats()
    block_count = db.get_block_count(config.get('syncer', 'main_chain'))
    tr_count = db.get_transaction_count()
    max_coin_supply = 84000000
    return NetworkStatsSerializer.to_web(stats, hash_rate[0], block_count, tr_count, max_coin_supply)

def get_bootstrap_link():
    bootstrap_dir = config.get('syncer', 'bootstrap_dir')

    bootstrap_path = os.path.join(bootstrap_dir, 'bootstrap.dat')
    if not os.path.isfile(bootstrap_path):
        return "Bootstrap.dat doesn't exist on the server", 404

    generated = os.stat(bootstrap_path).st_ctime
    bootstrap_server_path = os.path.join(
        config.get('syncer', 'bootstrap_dir_server_path'),
        'bootstrap.zip'
    )

    return {
        "url": bootstrap_server_path,
        "generated": generated
    }


def get_usd_price():
    stats = db.get_network_stats()
    return PriceSerializer.to_web(stats["usd_price"])

def get_price_history(limit,offset, since=None, until=None):
    if (since and (not isinstance(since, int))):
        return "From timestamp too large", 400
    elif (until and (not isinstance(until, int))):
        return "To timestamp is too large", 400

    price_history = db.get_latest_price_history(since, until, limit, offset)

    return [PriceHistorySerializer.to_web(history) for history in price_history]

def get_price_stats():
    try:
        return PriceStatsSerializer.to_web(db.get_price_stats())
    except KeyError:
        return "Price statistics not found", 404


##############
#   CLIENT   #
##############
def get_latest_sync_history(limit, offset):
    if not isinstance(offset, int):
        return "Offset too large", 400
    sync_history = db.get_latest_sync_history(limit, offset)
    return [SyncHistorySerializer.to_web(history) for history in sync_history]


def get_client_info():
    client_info = db.get_client_info()
    return ClientInfoSerializer.to_web(client_info)


############
#  SEARCH  #
############
def search(search_param):
    param_type = db.search(search_param)
    return SearchSerializer.to_web(search_param, param_type)


def create_and_run_app(port=5000):
    """
    Runs a new instance of a tornado server listening on the given port
    """
    api = connexion.App(__name__)
    api.add_api('explorer_api.yaml')
    CORS(api.app)
    api.run(server='tornado', port=port)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: python api.py [PORT]")
        sys.exit(1)

    create_and_run_app(int(sys.argv[1]))
