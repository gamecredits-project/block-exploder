class BlockFactory(object):
    def parsed_to_dict(self, parsed_block, chain):
        txids = [tx.txid for tx in parsed_block.tx]
        block_dict = parsed_block.to_dict()
        block_dict['tx'] = txids
        block_dict['target'] = hex(block_dict['target'])
        block_dict['chainwork'] = hex(block_dict['chainwork'])
        block_dict['chain'] = chain
        return block_dict


class VoutFactory(object):
    def parsed_to_mongo(self, parsed_vout, txid, index):
        vouts = []

        if parsed_vout.addresses:
            for adr in parsed_vout.addresses:
                vouts.append({
                    "txid": txid,
                    "index": index,
                    "asm": parsed_vout.asm,
                    "address": adr,
                    "type": parsed_vout.type,
                    "reqsigs": parsed_vout.reqsigs,
                    "hex": parsed_vout.hex,
                    "value": parsed_vout.value,
                })
        else:
            vouts = [{
                "txid": txid,
                "index": index,
                "asm": parsed_vout.asm,
                "address": parsed_vout.addresses,
                "type": parsed_vout.type,
                "reqsigs": parsed_vout.reqsigs,
                "hex": parsed_vout.hex,
                "value": parsed_vout.value,
            }]

        return vouts


class VinFactory(object):
    def parsed_to_mongo(self, parsed_vin, spender_txid):
        vin = parsed_vin.to_dict()
        vin['txid'] = spender_txid
        return vin
