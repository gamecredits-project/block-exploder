class VoutSerializer(object):
    @staticmethod
    def to_web(vout):
        return {
            "txid": vout.txid,
            "index": vout.index,
            "value": vout.value,
            "asm": vout.asm,
            "addresses": vout.addresses,
            "type": vout.type,
            "reqSigs": vout.reqSigs
        }

    @staticmethod
    def to_database(vout, txid, index):
        formatted = []

        if vout.addresses:
            for adr in vout.addresses:
                formatted.append({
                    "txid": txid,
                    "index": index,
                    "value": vout.value,
                    "asm": vout.asm,
                    "address": adr,
                    "type": vout.type,
                    "reqSigs": vout.reqSigs
                })
        else:
            formatted = [{
                "txid": vout.txid,
                "index": vout.index,
                "value": vout.value,
                "asm": vout.asm,
                "address": None,
                "type": vout.type,
                "reqSigs": vout.reqSigs
            }]

        return formatted


class VinSerializer(object):
    @staticmethod
    def to_web(vin):
        return {
            "vout_index": vin.vout_index,
            "prev_txid": vin.prev_txid,
            "sequence": vin.sequence,
            "hex": vin.hex,
            "txid": vin.txid,
            "coinbase": vin.coinbase
        }

    @staticmethod
    def to_database(vin, txid):
        return {
            "txid": txid,
            "prev_txid": vin.prev_txid,
            "vout_index": vin.vout_index,
            "hex": vin.hex,
            "sequence": vin.sequence,
            "coinbase": vin.coinbase
        }


class TransactionSerializer(object):
    @staticmethod
    def to_web(tr):
        return {
            "txid": tr.txid,
            "blocktime": tr.blocktime,
            "version": tr.version,
            "blockhash": tr.blockhash,
            "locktime": tr.locktime,
            "total": tr.total,
            "vin": tr.vin,
            "vout": tr.vout
        }

    @staticmethod
    def to_database(tr):
        formatted = {
            "version": tr.version,
            "locktime": tr.locktime,
            "txid": tr.txid,
            "vin": [],
            "vout": [],
            "total": tr.total,
            "blockhash": tr.blockhash,
            "blocktime": tr.blocktime
        }

        for v in tr.vin:
            formatted['vin'].append({
                "prev_txid": v.prev_txid,
                "vout_index": v.vout_index,
                "coinbase": v.coinbase
            })

        for v in tr.vout:
            formatted['vout'].append({
                "addresses": v.addresses,
                "type": v.type,
                "value": v.value
            })

        return formatted


class BlockSerializer(object):
    @staticmethod
    def to_web(block):
        return {
            "hash": block.hash,
            "size": block.size,
            "height": block.height,
            "version": block.version,
            "merkleroot": block.merkleroot,
            "tx": [tr.txid for tr in block.tx],
            "time": block.time,
            "nonce": block.nonce,
            "bits": block.bits,
            "difficulty": block.difficulty,
            "chainwork": block.chainwork,
            "previousblockhash": block.previousblockhash,
            "nextblockhash": block.nextblockhash,
            "target": block.target,
            "total": block.total,
        }

    @staticmethod
    def to_database(block):
        return {
            "hash": block.hash,
            "size": block.size,
            "height": block.height,
            "version": block.version,
            "merkleroot": block.merkleroot,
            "tx": [tr.txid for tr in block.tx],
            "time": block.time,
            "nonce": block.nonce,
            "bits": block.bits,
            "difficulty": str(block.difficulty),
            "chainwork": hex(block.chainwork),
            "previousblockhash": block.previousblockhash,
            "nextblockhash": block.nextblockhash,
            "target": hex(block.target),
            "dat": block.dat,
            "total": str(block.total),
            "work": block.work,
            "chain": block.chain
        }
