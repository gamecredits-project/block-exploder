import pymongo
from serializers import BlockSerializer
MAIN_CHAIN = 'main_chain'


class DatabaseGateway(object):
    def __init__(self, database):
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vin = database.vin
        self.vout = database.vout

    def get_latest_blocks(self, limit=25, offset=0):
        return list(self.blocks.find({"chain": MAIN_CHAIN})
                    .sort("height", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_block_by_hash(self, hash):
        block = self.blocks.find_one({"hash": hash})
        if block:
            return block
        raise KeyError("Block not found")

    def get_address_unspent(self, address):
        pass

    def get_transactions_by_address(self, address):
        txids = [v['txid'] for v in self.vout.find({"address": address})]
        return list(self.transactions.find({"txid": {"$in": txids}}))

    def get_transaction_by_txid(self, txid):
        pass

    def get_transactions_by_blockhash(self, blockhash):
        pass
