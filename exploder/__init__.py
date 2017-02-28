import datetime

from flask import Flask, render_template, jsonify, request
from blocker.core import Blockchain
from flask_humanize import Humanize

app = Flask(__name__)
app.config.from_object('exploder.config.Development')

humanize = Humanize(app)

chain = Blockchain(
    rpc_user=app.config['RPC_USER'],
    rpc_password=app.config['RPC_PASSWORD'],
    datadir_path=app.config['DATADIR_PATH']
)


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/blocks')
def blocks_json():
    num = int(request.args.get("num")) or 100
    offset = int(request.args.get("offset")) or 0

    blocks = [block.serialize() for block in chain.get_latest_blocks(num, offset)]

    return jsonify(blocks)


@app.route('/blocks/latest')
def latest_blocks():
    latest_blocks = [block.serialize() for block in chain.get_latest_blocks(5)]

    return jsonify(latest_blocks)


@app.route('/blocks/browse')
def browse_blocks():
    return render_template("browse_blocks.html")


@app.route('/blocks/<identifier>/transactions')
def block_transactions(identifier):
    block = chain.get_block(identifier)

    if not block:
        return "Block with hash or height %s doesn't exist" % hash, 404

    return jsonify([tr.serialize() for tr in chain.get_block_transactions(block)])


@app.route('/blocks/<identifier>')
def block_details(identifier):
    block = chain.get_block(identifier)

    if not block:
        return "Block with hash or height %s doesn't exist" % hash, 404

    block.confirmations = chain.calculate_block_confirmations(block)
    block.time = datetime.datetime.fromtimestamp(block.time).strftime("%Y-%m-%d %H:%M:%S")

    return render_template("block.html", block=block)


@app.route('/transactions/latest')
def latest_transactions():
    latest_transactions = [tr.serialize() for tr in chain.get_latest_transactions(5)]
    return jsonify(latest_transactions)


@app.route('/transactions/<txid>')
def transaction_details(txid):
    transaction = chain.get_transaction(txid)

    if not transaction:
        return "Transaction with txid %s doesn't exist" % txid, 404

    transaction.confirmations = chain.calculate_transaction_confirmations(transaction)
    transaction.time = datetime.datetime.fromtimestamp(transaction.time).strftime("%Y-%m-%d %H:%M:%S")

    transaction.blocktime = datetime.datetime.fromtimestamp(transaction.blocktime).strftime("%Y-%m-%d %H:%M:%S")

    return render_template("transaction.html", transaction=transaction)


@app.route('/network/status')
def network_status():
    return jsonify(chain.get_status())


@app.route('/network')
def network_details():
    disk_usages = chain.get_disk_usages()
    last_indexed_block = chain.height

    return render_template("network.html", disk_usages=disk_usages, last_indexed_block=last_indexed_block)


@app.route('/addresses/<identifier>')
def address_details(identifier):
    address = chain.get_address(identifier)

    for tr in address.transactions:
        tr.time = datetime.datetime.fromtimestamp(tr.time).strftime("%Y-%m-%d %H:%M:%S")

    if not address:
        return "Address %s doesn't exist in our database" % identifier, 404

    return render_template("address.html", address=address)


@app.route('/search/<query_string>')
def try_search(query_string):
    query_string = str(query_string)

    transaction = chain.get_transaction(query_string)
    if transaction:
        return jsonify({'url': '/transactions/%s' % transaction.txid})

    block = chain.get_block(query_string)
    if block:
        return jsonify({'url': '/blocks/%s' % block.hash})

    address = chain.get_address(query_string)
    if address:
        return jsonify({'url': '/addresses/%s' % address.address})

    return "No results found.", 404
