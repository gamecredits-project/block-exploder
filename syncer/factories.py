from gamecredits.entities import Block, BlockHeader, Transaction, Vout, Vin


class MongoBlockFactory(object):
    @staticmethod
    def from_mongo(mongo_block, mongo_block_transactions):
        if mongo_block is None:
            return None

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
            tx=[MongoTransactionFactory.from_mongo(tr) for tr in mongo_block_transactions],
            dat=mongo_block['dat'],
            nextblockhash=mongo_block['nextblockhash'],
            height=mongo_block['height'],
            chainwork=long(mongo_block['chainwork'], 16),
            chain=mongo_block['chain'],
            total=mongo_block['total']
        )


class MongoTransactionFactory(object):
    @staticmethod
    def from_mongo(tr):
        if tr is None:
            return None

        return Transaction(
            blocktime=tr['blocktime'],
            version=tr['version'],
            blockhash=tr['blockhash'],
            vin=[MongoVinFactory.from_mongo(v) for v in tr['vin']],
            vout=[MongoVoutFactory.from_mongo(v) for v in tr['vout']],
            locktime=tr['locktime'],
            total=tr['total'],
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
            addresses=mongo_vout.get('addresses'),
            type=mongo_vout['type'],
            asm=mongo_vout['asm'],
            spent=mongo_vout['spent']
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
