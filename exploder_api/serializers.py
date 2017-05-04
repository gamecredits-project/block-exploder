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


class VoutSerializer(object):
    @staticmethod
    def to_web(vout):
        return {
            "index": vout["index"],
            "reqSigs": vout["reqSigs"],
            "value": vout["value"],
            "txid": vout["txid"],
            "address": vout["address"],
            "type": vout["type"],
            "asm": vout["asm"]
        }
