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
            "chain": mongo_block["chain"],
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
            "mainChain": tr["main_chain"],
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
            "mainChain": tr["main_chain"],
            "reqSigs": tr["vout"]["reqSigs"],
            "spent": tr["vout"]["spent"],
            "txid": tr["vout"]["txid"],
            "type": tr["vout"]["type"],
            "value": tr["vout"]["value"],
            "blockTime": tr["blocktime"],
            "address": tr["vout"]["addresses"]
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
    def to_web(stats, hash_rate, num_blocks, num_transactions, max_coin_supply):
        return {
            "coinSupply": stats["supply"],
            "hashrate": hash_rate["hashrate"],
            "blockchainSize": stats["blockchain_size"],
            "numBlocks": num_blocks,
            "numTransactions": num_transactions,
            "coinMaxSupply": max_coin_supply
        }


class PriceSerializer(object):
    @staticmethod
    def to_web(price):
        return {
            "priceUSD": price
        }


class PriceHistorySerializer(object):
    @staticmethod
    def to_web(price_history):
        return {
            "priceUSD": price_history["price_usd"],
            "priceBTC": price_history["price_btc"],
            "marketCapUSD": price_history["market_cap_usd"],
            "timestamp": price_history["timestamp"]
        }


class PriceStatsSerializer(object):
    @staticmethod
    def to_web(price_stats):
        return {
            "priceUSD": price_stats["priceUSD"],
            "priceBTC": price_stats["priceBTC"],
            "percentChange24hUSD": price_stats["percentChange24hUSD"],
            "percentChange24hBTC": price_stats["percentChange24hBTC"],
            "volume24hUSD": price_stats["volume24hUSD"],
            "timestamp": price_stats["timestamp"]
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

class VolumesSerializer(object):
    @staticmethod
    def to_web(address, volume, volumes):
        return {
            "address": address,
            "totalVolume": volume,
            "volumes": volumes
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
