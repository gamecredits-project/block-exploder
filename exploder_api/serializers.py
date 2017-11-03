class BlockSerializer(object):
    @staticmethod
    def to_web(mongo_block):
        return {
            "hash": mongo_block["hash"],
            "size": mongo_block["size"],
            "height": mongo_block["height"],
            "version": mongo_block["version"],
            "merkleroot": mongo_block["merkleroot"],
            "tx": mongo_block["tx"],
            "time": mongo_block["time"],
            "nonce": mongo_block["nonce"],
            "bits": mongo_block["bits"],
            "difficulty": mongo_block["difficulty"],
            "chainwork": mongo_block["chainwork"],
            "previousblockhash": mongo_block["previousblockhash"],
            "nextblockhash": mongo_block["nextblockhash"],
            "target": mongo_block["target"],
            "total": mongo_block["total"],
            "work": mongo_block["work"]
        }


class TransactionSerializer(object):
    @staticmethod
    def to_web(tr):
        return {
            "txid": tr["txid"],
            "blocktime": tr["blocktime"],
            "version": tr["version"],
            "blockhash": tr["blockhash"],
            "locktime": tr["locktime"],
            "total": tr["total"],
            "vin": tr["vin"],
            "vout": tr["vout"]
        }

class UnspentTransactionSerializer(object):
    @staticmethod
    def to_web(tr):
        return {
            "asm": tr["vout"]["asm"],
            "index": tr["index"],
            "reqSigs": tr["vout"]["reqSigs"],
            "spent": tr["vout"]["spent"],
            "txid": tr["vout"]["txid"],
            "type": tr["vout"]["type"],
            "value": tr["vout"]["value"]
        }

class HashrateSerializer(object):
    @staticmethod
    def to_web(hash_rate):
        return {
            "hashrate": hash_rate["hashrate"],
            "timestamp": hash_rate["timestamp"]
        }


class SyncHistorySerializer(object):
    @staticmethod
    def to_web(sync_history):
        return {
            "startTime": sync_history["start_time"],
            "endTime": sync_history["end_time"],
            "startBlockHeight": sync_history["start_block_height"],
            "endBlockHeight": sync_history["end_block_height"]
        }


class NetworkStatsSerializer(object):
    @staticmethod
    def to_web(stats, hash_rate, num_blocks, num_transactions):
        return {
            "coinSupply": stats["supply"],
            "hashrate": hash_rate["hashrate"],
            "blockchainSize": stats["blockchain_size"],
            "numBlocks": num_blocks,
            "numTransactions": num_transactions
        }


class PriceSerializer(object):
    @staticmethod
    def to_web(price):
        return {
            "priceUSD": price
        }


class ClientInfoSerializer(object):
    @staticmethod
    def to_web(client_info):
        return {
            "ip": client_info["ip"],
            "version": client_info["version"],
            "peerInfo": client_info["peer_info"],
            "syncProgress": client_info["sync_progress"]
        }


class SearchSerializer(object):
    @staticmethod
    def to_web(search_param, param_type):
        return {
            "searchBy": search_param,
            "type": param_type
        }


class TransactoinCountSerializer(object):
    @staticmethod
    def to_web(address, num):
        return {
            "address": address,
            "transactionCount": num
        }


class VolumeSerializer(object):
    @staticmethod
    def to_web(address, volume):
        return {
            "address": address,
            "volume": volume
        }


class BalanceSerializer(object):
    @staticmethod
    def to_web(address, balance):
        return {
            "address": address,
            "balance": balance
        }

class AddressSerializer(object):
    @staticmethod
    def to_web(address):
        return{
            "address": address
        }
