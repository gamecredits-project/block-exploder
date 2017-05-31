import pymongo


class DatabaseGateway(object):
    def __init__(self, database, config):
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vin = database.vin
        self.vout = database.vout
        self.hashrate = database.hashrate
        self.network_stats = database.network_stats
        self.sync_history = database.sync_history
        self.client_info = database.client_info
        self.config = config

    def get_latest_blocks(self, limit=25, offset=0):
        return list(self.blocks.find({"chain": self.config.get('syncer', 'main_chain')})
                    .sort("height", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_block_by_hash(self, hash):
        block = self.blocks.find_one({"hash": hash})
        if block:
            return block
        raise KeyError("Block not found")

    def get_block_by_height(self, height):
        block = self.blocks.find_one({"height": height})
        if block:
            return block
        raise KeyError("Block not found")

    def get_address_unspent(self, address):
        trs = self.transactions.aggregate([
            {"$match": {"vout.addresses": address}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "vout_index"}},
            {"$match": {"vout.addresses": address}}
        ])

        unspent = []
        for tr in trs:
            spend = self.transactions.find_one({"vin.prev_txid": tr['txid'], "vin.vout_index": tr['vout_index']})

            if not spend:
                unspent.append(tr)

        for tr in unspent:
            del tr['_id']

        return unspent

    def get_address_transactions(self, address, limit=25, offset=0):
        return self.transactions.find({"vout.addresses": address})\
            .sort("blocktime", pymongo.DESCENDING).skip(offset).limit(limit)

    def get_address_volume(self, address):
        pipeline = [
            {"$match": {"vout.addresses": address}},
            {"$unwind": "$vout"},
            {"$match": {"vout.addresses": address}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "$vout.addresses", "volume": {"$sum": "$vout.value"}}}
        ]

        result = self.transactions.aggregate(pipeline)

        if not result:
            return 0

        return result.next()['volume']

    def get_transaction_by_txid(self, txid):
        tr = self.transactions.find_one({"txid": txid})

        if not tr:
            raise KeyError("Transaction with txid %s doesn't exist in the database" % txid)

        tr_block = self.get_block_by_hash(tr["blockhash"])
        tr['confirmations'] = self.calculate_block_confirmations(tr_block)

        return tr

    def get_transactions_by_blockhash(self, blockhash):
        tr = self.transactions.find({"blockhash": blockhash})

        if not tr:
            raise KeyError("Block with hash %s doesn't exist in the database" % blockhash)

        return list(tr)

    def get_latest_transactions(self, limit, offset):
        return list(self.transactions.find()
                    .sort("blocktime", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_highest_in_chain(self, chain):
        return self.blocks.find_one({"chain": chain}, sort=[("height", -1)])

    def calculate_block_confirmations(self, block):
        highest_in_chain = self.get_highest_in_chain(block['chain'])
        return highest_in_chain['height'] - block['height']

    def get_latest_hashrates(self, limit):
        return list(self.hashrate.find().sort("timestamp", pymongo.DESCENDING).limit(limit))

    def get_block_count(self):
        return self.blocks.count()

    def get_transaction_count(self):
        return self.transactions.count()

    def get_network_stats(self):
        return self.network_stats.find_one()

    def get_latest_sync_history(self, limit, offset):
        return list(self.sync_history.find()
                    .sort("end_time", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_client_info(self):
        return self.client_info.find_one()
