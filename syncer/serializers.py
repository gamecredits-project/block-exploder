import time


class VoutSerializer(object):
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
    def to_database(block):
        if not type(block.tx[0]) == unicode:
            tx = [tr.txid for tr in block.tx]
        else:
            tx = block.tx

        return {
            "hash": block.hash,
            "size": block.size,
            "height": block.height,
            "version": block.version,
            "merkleroot": block.merkleroot,
            "tx": tx,
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


class HashrateSerializer(object):
    @staticmethod
    def to_database(rate):
        return {
            "hashrate": rate,
            "timestamp": time.time()
        }


class SyncHistorySerializer(object):
    @staticmethod
    def to_database(start_time, end_time, start_block_height, end_block_height):
        return {
            "start_time": start_time,
            "end_time": end_time,
            "start_block_height": start_block_height,
            "end_block_height": end_block_height
        }
