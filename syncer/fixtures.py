EXAMPLE_MONGO_BLOCK = {
    "_id": "58da5ca763623909fa6e7d02",
    "merkleroot": "79788343e8d6128fae906a47d9307aab632f0bdbc536535879f4dd6fe7483db0",
    "nonce": "2992179712",
    "previousblockhash": "63dc93df34bb78f590c30129150ff80302cf28ea38324b53abe378e5cbea8159",
    "hash": "8878fb77499663ea297c7f4940db5bbd726d31c8405fa5d2a5831c89fb7108e5",
    "chainwork": "0x342e5561ec66",
    "tx": [
        "0bd3847ef6dd4f978535635cbdb0f236baa7039d74a609eaf8216d8e34388797"
    ],
    "work": 48244858,
    "height": 302953,
    "dat": {
        "index": 1,
        "end": 34769,
        "start": 34556
    },
    "difficulty": 0.01123288,
    "nextblockhash": "f100067614aa221b13771d6976fc23fa00f8ad8133950762fa8a1abbf1cc1e55",
    "version": 2,
    "target": "0x59063c0000000000000000000000000000000000000000000000000000L",
    "time": 1403995627,
    "chain": 0,
    "total": 50,
    "bits": "0x1d59063c",
    "size": 205
}

EXAMPLE_RPC_BLOCK = {
    "hash": "aa966a65eca209291c6ba2a8c8a3a34f1860741ea510bb406eca7c92b994a31d",
    "confirmations": 1625261,
    "size": 188,
    "height": 500,
    "version": 2,
    "merkleroot": "83dba4445b237b58b4ff1af5a62eaa2f799376851f1f065933c60945d68bd6e2",
    "tx": [
        "83dba4445b237b58b4ff1af5a62eaa2f799376851f1f065933c60945d68bd6e2"
    ],
    "time": 1392769043,
    "nonce": 1546981888,
    "bits": "1e0ffff0",
    "difficulty": 0.00024414,
    "chainwork": "000000000000000000000000000000000000000000000000000000001f501f50",
    "previousblockhash": "f60288630bdb2268882e96f1b468e16c44ebf3cc8045d50f470e10ac046a9961",
    "nextblockhash": "65e6916602e31f2ee420bfd38cba396444c153cf67ff3db3e42b7a5aaa010ed9"
}

EXAMPLE_RPC_TRANSACTION = {
    "hex": "01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff5f03712d14062f503253482f04efb0fc5608fabe6d6d4cc4873df0b7d2ad01c7a9711f47944fb869dd63f87290e0c311a2ffc7fe25370800000000000000600000140f0000001931333835333838352f6d696e65722073686172705f66697265000000000100f90295000000001976a914caa8a50bdb3eb48698b0387554879145857c11c088ac00000000",
    "txid": "358b6f89ed4fa238fb6ad36faa1a6a615a87a6e5195d626d599716b4ba2f11af",
    "version": 1,
    "locktime": 0,
    "vin": [
        {
            "coinbase": "03712d14062f503253482f04efb0fc5608fabe6d6d4cc4873df0b7d2ad01c7a9711f47944fb869dd63f87290e0c311a2ffc7fe25370800000000000000600000140f0000001931333835333838352f6d696e65722073686172705f66697265",
            "sequence": 0
        }
    ],
    "vout": [
        {
            "value": 25.00000000,
            "n": 0,
            "scriptPubKey": {
                "asm": "OP_DUP OP_HASH160 caa8a50bdb3eb48698b0387554879145857c11c0 OP_EQUALVERIFY OP_CHECKSIG",
                "hex": "76a914caa8a50bdb3eb48698b0387554879145857c11c088ac",
                "reqSigs": 1,
                "type": "pubkeyhash",
                "addresses": [
                    "GcKUwWw8nUxPHwZG4pLzSFHVKiEw9MxnVG"
                ]
            }
        }
    ],
    "blockhash": "3d8bd6ecd7b69ca815249afdbb704a3e8f2370f2aed8d546d632df5b4f05ebe2",
    "confirmations": 304256,
    "time": 1459400940,
    "blocktime": 1459400940
}
