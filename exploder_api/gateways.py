import pymongo
import sys

from helpers import validate_address, check_parameter_if_int, confirmations_from_rpc

class DatabaseGateway(object):
    def __init__(self, database, config):
        self.blocks = database.blocks
        self.transactions = database.transactions
        self.vin = database.vin
        self.vout = database.vout
        self.hashrate = database.hashrate
        self.network_stats = database.network_stats
        self.price_history = database.price_history
        self.price_stats = database.price_stats
        self.sync_history = database.sync_history
        self.client_info = database.client_info
        self.config = config

    ############
    #  BLOCKS  #
    ############
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

    def get_highest_in_chain(self, chain):
        return self.blocks.find_one({"chain": chain}, sort=[("height", -1)])

    def calculate_block_confirmations(self, block, rpc):
        highest_in_chain = self.get_highest_in_chain(block['chain'])

        if highest_in_chain['chain'] != 'main_chain':
            block_confirmations = confirmations_from_rpc(rpc, block)
        else:
            block_confirmations = highest_in_chain['height'] - block['height']

        return block_confirmations

    def get_block_count(self, chain):
        return self.blocks.find({"chain": chain}).count()

    ###############
    #  ADDRESSES  #
    ###############
    def get_address_unspent(self, address, start, limit):
        if not start:
            unspent = self.transactions.aggregate([
                {"$match": {"vout.addresses": address}},
                {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
                {"$project": {"vout": 1, "txid": 1, "index": 1, "blocktime": 1, "main_chain": 1}},
                {"$match": {"vout.spent": False, "vout.addresses": address}},
                {"$sort": {"blocktime": -1}},
                {"$limit": limit}
                ])

            results = []
            for uns in unspent:
                uns['vout']['txid'] = uns['txid']
                uns['vout']['index'] = uns['index']
                results.append(uns)

            return results

        unspent = self.transactions.aggregate([
            {"$match": {"vout.addresses": address}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
            {"$project": {"vout": 1, "txid": 1, "index": 1, "blocktime": 1, "main_chain": 1}},
            {"$match": {"vout.spent": False, "vout.addresses": address,
                        "blocktime": {"$lt": start}}},
            {"$sort": {"blocktime": -1}},
            {"$limit": limit}
            ])

        results = []
        for uns in unspent:
            uns['vout']['txid'] = uns['txid']
            uns['vout']['index'] = uns['index']
            results.append(uns)

        return results

    def post_addresses_unspent(self, addresses, start, limit):
        if not start:
            pipeline = [
                {"$match": {"vout.addresses": {"$in": addresses}}},
                {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
                {"$project": {"vout": 1, "txid": 1, "index": 1, "blocktime": 1, "main_chain": 1}},
                {"$match": {"vout.spent": False, "vout.addresses": {"$in": addresses}}},
                {"$sort": {"blocktime": -1}},
                {"$limit": limit}
            ]

            unspent = self.transactions.aggregate(pipeline)

            results = []
            for uns in unspent:
                uns['vout']['txid'] = uns['txid']
                uns['vout']['index'] = uns['index']
                results.append(uns)

            return results

        pipeline = [
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "index"}},
            {"$project": {"vout": 1, "txid": 1, "index": 1, "blocktime": 1, "main_chain": 1}},
            {"$match": {"vout.spent": False, "vout.addresses": {"$in": addresses},
                        "blocktime" : {"$lt": start}}},
            {"$sort": {"blocktime": -1}},
            {"$limit": limit}
        ]

        unspent = self.transactions.aggregate(pipeline)

        results = []
        for uns in unspent:
            uns['vout']['txid'] = uns['txid']
            uns['vout']['index'] = uns['index']
            results.append(uns)

        return results



    def get_address_balance(self, address):
        result = self.transactions.aggregate([
            {"$match": {"vout.addresses": address}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "vout_index"}},
            {"$match": {"vout.spent": True, "vout.addresses": address, "main_chain": True}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "$vout.addresses", "balance": {"$sum": "$vout.value"}}}
        ])

        result = list(result)

        if not result:
            return 0

        return result[0]['balance']

    def post_addresses_balance(self, addresses):
        result = self.transactions.aggregate([
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": {"path": "$vout", "includeArrayIndex": "vout_index"}},
            {"$match": {"vout.spent": True, "main_chain": True, "vout.addresses":{"$in": addresses }}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "vout", "balance": {"$sum": "$vout.value"}}}
        ])

        result = list(result)

        if not result:
            return 0

        return result[0]['balance']


    def get_address_transactions(self, address, start, limit):
        if not start:
            return list(self.transactions.find({"vout.addresses": address})
                        .sort("blocktime", pymongo.DESCENDING).limit(limit))

        return list(self.transactions.find({"vout.addresses": address, "blocktime": {"$lt": start}})
                    .sort("blocktime", pymongo.DESCENDING).limit(limit))


    def post_addresses_transactions(self, addresses, start, limit):
        if not start:
            return list(self.transactions.find({"vout.addresses": {"$in": addresses}})
                        .sort("blocktime", pymongo.DESCENDING).limit(limit))

        return list(self.transactions.find(
            {"vout.addresses": {"$in": addresses}, "blocktime": {"$lt": start}})
                    .sort("blocktime", pymongo.DESCENDING).limit(limit))

    def get_address_num_transactions(self, address):
        pipeline = [
            {"$match": {"vout.addresses": address}},
            {"$project": {"vout.addresses": 1}},
            {"$group": {"_id": "vout.addresses", "num_transactions": {"$sum": 1}}}
        ]

        result = self.transactions.aggregate(pipeline)

        result = list(result)
        if not result:
            return 0

        return result[0]['num_transactions']

    def post_addresses_num_transactions(self, addresses):
        pipeline = [
            {"$match": {"vout.addresses": {"$in":addresses}}},
            {"$project": {"vout.addresses": 1}},
            {"$group": {"_id": "vout.addresses", "num_transactions": {"$sum": 1}}}
        ]

        result = self.transactions.aggregate(pipeline)

        result = list(result)
        if not result:
            return 0

        return result[0]['num_transactions']

    def get_address_volume(self, address):
        # Check if the address is unused on the blockchain
        if not self.transactions.find_one({"vout.addresses": address}):
            return 0

        pipeline = [
            {"$match": {"vout.addresses": address}},
            {"$unwind": "$vout"},
            {"$match": {"vout.addresses": address, "main_chain": True}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group": {"_id": "$vout.addresses", "volume": {"$sum": "$vout.value"}}}
        ]

        result = self.transactions.aggregate(pipeline)

        if not result:
            return 0

        return result.next()['volume']

    def post_addresses_volume(self, addresses):
        # Check if the address is unused on the blockchain
        pipeline = [
            {"$match": {"vout.addresses": {"$in": addresses}}},
            {"$unwind": "$vout"},
            {"$match": {"vout.addresses": {"$in": addresses}, "main_chain": True}},
            {"$project": {"vout.addresses": 1, "vout.value": 1}},
            {"$group":
                {
                    "_id": "$vout.addresses",
                    "volume": {"$sum":"$vout.value"}
                }
            }
        ]

        result = self.transactions.aggregate(pipeline)        
        result = list(result)

        addresses = set(addresses)
        total_volume = 0

        for _, address in enumerate(set(addresses)):
            if _ >= len(result):
                pass
            else:
                result[_]['address'] = result[_]['_id'][0].strip('[]')
                del result[_]['_id']
                mongo_address = result[_]['address']
                
                if mongo_address in addresses:
                    addresses.remove(mongo_address)
                    total_volume += (result[_]['volume'])

        for address in addresses:
            result.append({'volume': 0, 'address': address})

        if not result:
            return 0

        return result, total_volume


    ##################
    #  TRANSACTIONS  #
    ##################
    def get_transaction_by_txid(self, txid, rpc):
        tr = self.transactions.find_one({"txid": txid})

        if not tr:
            raise KeyError("Transaction with txid %s doesn't exist in the database" % txid)

        tr_block = self.get_block_by_hash(tr["blockhash"])
        tr['confirmations'] = self.calculate_block_confirmations(tr_block, rpc)

        return tr

    def get_transactions_by_blockhash(self, blockhash):
        tr = self.transactions.find({"blockhash": blockhash})

        if not tr:
            raise KeyError("Block with hash %s doesn't exist in the database" % blockhash)

        return list(tr)

    def get_latest_transactions(self, limit, offset):
        return list(self.transactions.find({"main_chain": True})
                    .sort("blocktime", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_transaction_count(self):
        return self.transactions.count()

    #############
    #  NETWORK  #
    #############
    def get_latest_hashrates(self, limit):
        return list(self.hashrate.find().sort("timestamp", pymongo.DESCENDING).limit(limit))

    def get_network_stats(self):
        return self.network_stats.find_one()

    ##########################
    #   PRICE HISTORY/STATS  #
    ##########################
    def get_latest_price_history(self, since, until, limit, offset):
        # Check if there are any parameters, if not get everything from history
        if not since and not until and not limit:
            return list(self.price_history.find()
                        .sort("timestamp", pymongo.DESCENDING).skip(offset))

        # Check if there are since and until
        if not since and not until:
            return list(self.price_history.find()
                        .sort("timestamp", pymongo.DESCENDING).skip(offset).limit(limit))

        if not until:
            if not limit:
                return list(self.price_history.find({"timestamp": {"$gte": since}})
                            .sort("timestamp", pymongo.DESCENDING).skip(offset))

            return list(self.price_history.find({"timestamp": {"$gte": since}})
                        .sort("timestamp", pymongo.DESCENDING).skip(offset).limit(limit))

        if not since:
            if not limit:
                return list(self.price_history.find({"timestamp": {"$lte": until}})
                            .sort("timestamp", pymongo.DESCENDING).skip(offset))

            return list(self.price_history.find({"timestamp": {"$lte": until}})
                        .sort("timestamp", pymongo.DESCENDING).skip(offset).limit(limit))

        # If we have all parameters
        return list(self.price_history.find({"timestamp": {"$gte": since, "$lte": until}})
                    .sort("timestamp", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_price_stats(self):
        price_stats = self.price_stats.find_one()
        if price_stats:
            return price_stats
        raise KeyError("Price statistics not found")

    ############
    #  CLIENT  #
    ############
    def get_latest_sync_history(self, limit, offset):
        return list(self.sync_history.find()
                    .sort("end_time", pymongo.DESCENDING).skip(offset).limit(limit))

    def get_client_info(self):
        return self.client_info.find_one()

    ############
    #  SEARCH  #
    ############
    def search(self, parameter):
        """
        Search blocks, transactions and addresses for :parameter:

        @param parameter: Block hash, transaction id or address hash
        @type parameter: string
        @return: Type of the parameter if successful, otherwise None
        @rtype: string
        """
        if parameter:
            # Only check if address is valid
            # (address exists even if noone has claimed it yet)

            # Implement over and under flow catch error
            if validate_address(parameter):
                return "address"
            block = self.blocks.find_one({"hash": parameter})
            if block:
                return "block"
            if parameter.isdigit():
                if len(str(int(parameter))) <= len(str(int(sys.maxint))):
                    height = self.blocks.find_one({"height": int(parameter)})
                    if height:
                        return "block"
            transaction = self.transactions.find_one({"txid": parameter})
            if transaction:
                return "transaction"

        return None
