import unittest

from mock import patch, MagicMock, PropertyMock
from exploder import chain as unmocked
from blocker.core import Block, Transaction
import sys
import StringIO

# Global variables are evil
BULK_START = 180
FAKE_BLOCK_COUNT = 200


class BlockchainTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chain = unmocked

    def setUp(self):
        self.exampleRpcBlock = {
            "hash": "fc5d20c81a0e1bb71bb8afed10783e6f2291452f927c6c36500d0890b2e4e1a2",
            "confirmations": 1576696,
            "size": 188,
            "height": 23345,
            "version": 2,
            "merkleroot": "fccbc6320f3dc1d58c45d7a37781ff7b1a6908ac9d508729e631a95074ab65f2",
            "tx": [
                "fccbc6320f3dc1d58c45d7a37781ff7b1a6908ac9d508729e631a95074ab65f2",
                "fccbc6320f3dc1d58c45d7a37781ff7b1a6908ac9d508729e631a95074ab65f2",  # duplicate for tests
            ],
            "time": 1395389077,
            "nonce": 2519663616,
            "bits": "1d22544b",
            "difficulty": 0.02912922,
            "chainwork": "00000000000000000000000000000000000000000000000000001063415758e1",
            "previousblockhash": "2b505fce8fa467d3db7d0723a46dad1d3eea6b47fe97d32e0e418a6bf3b81d02",
            "nextblockhash": "13596dfd63ef1288d7ad712021e0b25c76a16da08fb8a95eaf1dcca76660dba2"
        }

        self.exampleRpcTransaction = {
            "hex": "0100000001000000000000000000000000000000000000000000",
            "txid": "fccbc6320f3dc1d58c45d7a37781ff7b1a6908ac9d508729e631a95074ab65f2",
            "version": 1,
            "locktime": 0,
            "vin": [
                {
                    "coinbase": "02315b010f062f503253482f",
                    "sequence": 4294967295
                }
            ],
            "vout": [
                {
                    "value": 50.00000000,
                    "n": 0,
                    "scriptPubKey": {
                        "asm": "020f9a2dfe5ea85757c2d583208e9bfc82041f47b8d69aa78ce30df2de2322e1d5 OP_CHECKSIG",
                        "hex": "21020f9a2dfe5ea85757c2d583208e9bfc82041f47b8d69aa78ce30df2de2322e1d5ac",
                        "reqSigs": 1,
                        "type": "pubkey",
                        "addresses": [
                            "GN5Q5kwha6yBEYmX9WffRDLe9NoP2EbjEL"
                        ]
                    }
                }
            ],
            "blockhash": "fc5d20c81a0e1bb71bb8afed10783e6f2291452f927c6c36500d0890b2e4e1a2",
            "confirmations": 1576736,
            "time": 1395389077,
            "blocktime": 1395389077
        }

        self.exampleBlock = Block(self.exampleRpcBlock)
        self.exampleTransaction = Transaction(self.exampleRpcTransaction)

        self.chain.blocks = MagicMock()
        self.chain.transactions = MagicMock()
        self.chain.addresses = MagicMock()
        self.chain.rpc = MagicMock()

        self.chain.rpc.getblockcount.return_value = FAKE_BLOCK_COUNT
        self.chain.rpc.getblock.return_value = self.exampleRpcBlock
        self.chain.rpc.getrawtransaction.return_value = self.exampleRpcTransaction

        self.chain._get_highest_block = MagicMock(return_value=self.exampleBlock)

    def test_height_returns_zero(self):
        """
        If there are no blocks in the DB the height
        of the chain should be zero
        """
        with patch.object(self.chain, '_get_highest_block') as patch_latest_block:
            patch_latest_block.return_value = None
            self.assertEqual(self.chain.height, 0)

    def _check_output(self, keyword, function_to_call):
        """
        Checks for keyword in stdout output of a given function
        """
        saved_stdout = sys.stdout
        try:
            out = StringIO.StringIO()
            sys.stdout = out
            function_to_call()
            output = out.getvalue().strip()
            return keyword in output
        finally:
            sys.stdout = saved_stdout

    def test_last_known_nextblockhash_updated(self):
        """
        When the sync starts the last known block hash should be updated
        """
        self.exampleBlock.nextblockhash = None
        with patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=180):
            with patch('blocker.core.Blockchain._get_highest_block', return_value=self.exampleBlock):
                with patch('blocker.core.Block.update_nextblockhash') as mock_update_nextblockhash:
                    self.chain.sync()
                    self.assertTrue(mock_update_nextblockhash.called)

    ##################
    # BULK SYNC TESTS
    ##################
    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=BULK_START)
    def test_bulk_sync_starts(self, mock_height):
            # Check that the [BULK] keyword is in output
            self.assertTrue(self._check_output("[BULK]", self.chain.sync))

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=BULK_START)
    def test_bulk_exactly_n_blocks_inserted(self, mock_height):
            synced_blocks = self.chain.sync()
            # insert many is called once with many blocks
            self.assertEqual(self.chain.blocks.insert_many.call_count, 1)
            self.assertEqual(len(self.chain.blocks.insert_many.call_args[0][0]), FAKE_BLOCK_COUNT - BULK_START)
            self.assertEqual(len(self.chain.blocks.insert_many.call_args[0][0]), synced_blocks)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=BULK_START)
    def test_bulk_exact_number_transactions_inserted(self, mock_height):
            self.chain.sync()
            num_blocks = FAKE_BLOCK_COUNT - BULK_START
            tr_per_block = self.exampleBlock.num_transactions
            # Check if all transactions are inserted
            self.assertEqual(len(self.chain.transactions.insert_many.call_args[0][0]), num_blocks * tr_per_block)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=BULK_START)
    def test_bulk_exact_number_addresses_inserted(self, mock_height):
            self.chain.sync()
            num_blocks = FAKE_BLOCK_COUNT - BULK_START
            tr_per_block = self.exampleBlock.num_transactions
            adr_per_tr = len(self.exampleRpcTransaction["vout"][0]["scriptPubKey"]["addresses"])
            # Check if all addresses are inserted
            self.assertEqual(len(self.chain.addresses.insert_many.call_args[0][0]),
                             num_blocks * tr_per_block * adr_per_tr)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=BULK_START)
    def test_bulk_block_total(self, mock_height):
            self.chain.sync()
            total = len(self.exampleRpcBlock["tx"]) *\
                sum([float(vout["value"]) for vout in self.exampleRpcTransaction["vout"]])

            [self.assertEqual(block["total"], total) for block in self.chain.blocks.insert_many.call_args[0][0]]

    #########################
    # SINGLE BLOCK SYNC TESTS
    #########################
    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=199)
    def test_single_sync_starts(self, mock_height):
            # Check there's no [BULK] keyword in stdout output
            self.assertFalse(self._check_output("[BULK]", self.chain.sync))

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=199)
    def test_single_exactly_one_block_inserted(self, mock_height):
        synced_blocks = self.chain.sync()
        self.assertEqual(self.chain.blocks.insert_one.call_count, 1)
        self.assertEqual(self.chain.blocks.insert_one.call_count, synced_blocks)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=199)
    def test_single_exact_number_transactions_inserted(self, mock_height):
        self.chain.sync()
        self.assertEqual(self.chain.transactions.insert_one.call_count, self.exampleBlock.num_transactions)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=199)
    def test_single_exact_number_addresses_inserted(self, mock_height):
        self.chain.sync()
        num_addresses = len(self.exampleRpcBlock["tx"]) *\
            len(self.exampleRpcTransaction["vout"][0]["scriptPubKey"]["addresses"])

        self.assertEqual(self.chain.addresses.insert_one.call_count, num_addresses)

    @patch('blocker.core.Blockchain.height', new_callable=PropertyMock, return_value=199)
    def test_single_block_total(self, mock_height):
        self.chain.sync()
        block = self.chain.blocks.insert_one.call_args[0][0]
        total = len(self.exampleRpcBlock["tx"]) *\
            sum([float(vout["value"]) for vout in self.exampleRpcTransaction["vout"]])

        self.assertEqual(block["total"], total)


if __name__ == '__main__':
    unittest.main()
