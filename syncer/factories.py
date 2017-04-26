from gamecredits.entities import Block, BlockHeader, Transaction, Vout, Vin


class MongoBlockFactory(object):
    @staticmethod
    def from_mongo(mongo_block):
        header = BlockHeader(
            hash=mongo_block['hash'],
            version=mongo_block['version'],
            previousblockhash=mongo_block['previousblockhash'],
            merkleroot=mongo_block['merkleroot'],
            time=mongo_block['time'],
            bits=mongo_block['bits'],
            target=long(mongo_block['target'], base=16),
            difficulty=mongo_block['difficulty'],
            nonce=mongo_block['nonce'],
            work=mongo_block['work']
        )

        return Block(
            size=mongo_block['size'],
            header=header,
            tx=mongo_block['tx'],
            dat=mongo_block['dat'],
            nextblockhash=mongo_block['nextblockhash'],
            height=mongo_block['height'],
            chainwork=int(mongo_block['chainwork'], 16),
            chain=mongo_block['chain'],
            total=mongo_block['total']
        )


class MongoTransactionFactory(object):
    @staticmethod
    def from_mongo(tr):
        vout = []
        for v in tr['vout']:
            vout.append({
                "type": v["type"],
                "addresses": v.get("addresses"),
                "value": v.get("value")
            })

        vin = []
        for v in tr['vin']:
            vin.append({
                "coinbase": v.get("coinbase"),
                "vout_index": v.get("vout_index"),
                "prev_txid": v.get("prev_txid")
            })

        return Transaction(
            blocktime=tr['blocktime'],
            version=tr['version'],
            blockhash=tr['blockhash'],
            vout=vout,
            locktime=tr['locktime'],
            total=tr['total'],
            vin=vin,
            txid=tr['txid']
        )


class MongoVoutFactory(object):
    @staticmethod
    def from_mongo(mongo_vout):
        return Vout(
            index=mongo_vout.get('index'),
            reqSigs=mongo_vout.get('reqSigs'),
            value=mongo_vout.get('value'),
            txid=mongo_vout.get('txid'),
            addresses=[mongo_vout.get('address')],
            type=mongo_vout['type'],
            asm=mongo_vout['asm']
        )


class MongoVinFactory(object):
    @staticmethod
    def from_mongo(mongo_vin):
        return Vin(
            prev_txid=mongo_vin.get('prev_txid'),
            vout_index=mongo_vin.get('vout_index'),
            hex=mongo_vin.get('hex'),
            sequence=mongo_vin.get('sequence'),
            coinbase=mongo_vin.get('coinbase'),
            txid=mongo_vin.get('txid')
        )
