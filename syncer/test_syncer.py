import unittest
from mock import patch, MagicMock, PropertyMock
from interactors import ExploderSyncer, MAIN_CHAIN
from factories import BlockFactory
from gateways import DatabaseGateway
from fixtures import *
import copy


class InitialSyncTestCase(unittest.TestCase):
    """
    Sync is ran for the first time, should be read from the stream (.dat files).
    """
    def setUp(self):
        self.fake_mongo = MagicMock()
        self.fake_mongo.blocks.find_one.return_value = None

        self.fake_rpc = MagicMock()
        self.fake_rpc.getblockcount = MagicMock(return_value=10000)

        self.db = DatabaseGateway(database=self.fake_mongo, cache_size=1000)
        self.db.highest_block = PropertyMock(return_value=None)

        self.chain = ExploderSyncer(
            database=self.db,
            blocks_dir="/home/vagrant/.gamecredits/blocks/",
            rpc_client=self.fake_rpc
        )

    def test_database_initialized_correctly(self):
        # caches are initialized and empty
        self.assertEqual(self.db.block_cache, {})
        self.assertEqual(self.db.tr_cache, [])
        self.assertEqual(self.db.vin_cache, [])
        self.assertEqual(self.db.vout_cache, [])

        # Indexes are created
        self.assertTrue(self.db.blocks.create_index.called)

    def test_blockchain_initialized_correctly(self):
        # First iter is true
        self.assertTrue(self.chain.first_iter)

        # chain peak is None
        self.assertIsNone(self.chain.chain_peak)

        # blockfiles are found
        self.assertGreater(len(self.chain.blk_files), 0)

    def test_no_blk_files_skipped(self):
        """
        No block files should be skipped on initial sync
        """
        files_before = self.chain.blk_files
        self.chain.sync(limit=3)
        self.assertEqual(files_before, self.chain.blk_files)

    @patch('interactors.open')
    def test_stream_seek_not_called(self, mock_open):
        """
        No seek should be called on initial sync
        """
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream

        # has_length will raise type error because
        # MagicMock is not a file
        with self.assertRaises(TypeError):
            self.chain.sync(limit=3)
            self.assertTrue(mock_open.called)
            self.assertFalse(mock_stream.seek.called)

    def test_rpc_sync_not_called(self):
        self.chain._sync_rpc = MagicMock()
        self.assertFalse(self.chain._sync_rpc.called)


class SyncStreamTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_mongo = MagicMock()
        self.fake_mongo.blocks.find_one.return_value = None

        self.fake_rpc = MagicMock()
        self.fake_rpc.getblockcount = MagicMock(return_value=10000)

        self.db = DatabaseGateway(database=self.fake_mongo, cache_size=1000)
        self.db.highest_block = PropertyMock(return_value=None)

        self.chain = ExploderSyncer(
            database=self.db,
            blocks_dir="/home/vagrant/.gamecredits/blocks/",
            rpc_client=self.fake_rpc
        )

        self.example_block = BlockFactory.from_mongo(EXAMPLE_MONGO_BLOCK)

    def test_block_files_get_skipped(self):
        files_before = self.chain.blk_files
        self.chain._sync_stream(highest_known=self.example_block, client_height=10000, limit=100)
        self.assertNotEqual(files_before, self.chain.blk_files)

    @patch('interactors.open')
    def test_stream_seek_called(self, mock_open):
        mock_stream = MagicMock()
        mock_open.return_value = mock_stream

        # has_length will raise type error because
        # MagicMock is not a file
        with self.assertRaises(TypeError):
            self.chain.sync(limit=3)
            self.assertTrue(mock_open.called)
            self.assertTrue(mock_stream.seek.called)

    def test_parse_100_blocks_from_zero_height(self):
        self.chain.handle_stream_block = MagicMock()
        self.chain.db.put_transactions = MagicMock()
        self.chain._update_progress = MagicMock()

        parsed = self.chain._sync_stream(highest_known=None, client_height=1000, limit=100)

        self.assertEqual(parsed, 100)
        self.assertEqual(self.chain.handle_stream_block.call_count, 100)
        self.assertEqual(self.chain.db.put_transactions.call_count, 100)
        self.assertEqual(self.chain._update_progress.call_count, 100)


class HandleStreamBlockTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_mongo = MagicMock()
        self.fake_mongo.blocks.find_one.return_value = None

        self.fake_rpc = MagicMock()
        self.fake_rpc.getblockcount = MagicMock(return_value=10000)

        self.db = DatabaseGateway(database=self.fake_mongo, cache_size=1000)
        self.db.highest_block = PropertyMock(return_value=None)

        self.chain = ExploderSyncer(
            database=self.db,
            blocks_dir="/home/vagrant/.gamecredits/blocks/",
            rpc_client=self.fake_rpc
        )

        self.example_block = BlockFactory.from_mongo(EXAMPLE_MONGO_BLOCK)

    def test_chain_peak_is_none_should_create_coinbase(self):
        self.chain.chain_peak = None
        block = self.chain.handle_stream_block(block=self.example_block)

        self.assertEqual(block.height, 0)
        self.assertEqual(block.chainwork, block.work)
        self.assertEqual(block.chain, MAIN_CHAIN)

        self.assertEqual(self.chain.chain_peak, block)
        self.assertFalse(self.chain.first_iter, False)

    def test_append_to_main_chain(self):
        self.chain.db.put_block = MagicMock()

        stream = open(self.chain.blk_files[0], 'r')
        block1 = BlockFactory.from_stream(stream)['block']
        block2 = BlockFactory.from_stream(stream)['block']
        self.chain.handle_stream_block(block1)
        added_block = self.chain.handle_stream_block(block2)

        self.assertEqual(added_block.height, block1.height + 1)
        self.assertEqual(added_block.chainwork, block1.chainwork + block2.work)
        self.assertEqual(added_block.chain, 0)
        self.assertEqual(self.chain.chain_peak.hash, block2.hash)

        # Persistence check
        self.assertEqual(self.chain.db.put_block.call_count, 1)

    def test_fork_no_reconverge(self):
        # Create 3 blocks
        stream = open(self.chain.blk_files[0], 'r')
        block1 = BlockFactory.from_stream(stream)['block']
        block2 = BlockFactory.from_stream(stream)['block']
        block3 = BlockFactory.from_stream(stream)['block']

        # Mock reconverge method
        self.chain.reconverge = MagicMock()

        # Simulate fork - the 3rd block now points to the 1st
        # instead to the 2nd block so it forks from the main chain
        block3.previousblockhash = block1.hash

        self.chain.handle_stream_block(block1)
        self.chain.handle_stream_block(block2)

        added = self.chain.handle_stream_block(block3)

        # The added block should not be on the main chain
        self.assertEqual(added.chain, MAIN_CHAIN + 1)
        self.assertEqual(added.height, block1.height + 1)

        # Reconverge shouldn't be called
        self.assertFalse(self.chain.reconverge.called)

    def test_fork_reconverge(self):
        # Create 3 blocks
        stream = open(self.chain.blk_files[0], 'r')
        block1 = BlockFactory.from_stream(stream)['block']
        block2 = BlockFactory.from_stream(stream)['block']
        block3 = BlockFactory.from_stream(stream)['block']

        # Simulate fork - the 3rd block now points to the 1st
        # instead to the 2nd block so it forks from the main chain
        block3.previousblockhash = block1.hash

        # Increase work so reconverge happens
        block3.work = block3.work + 1000000000

        self.chain.handle_stream_block(block1)
        added = self.chain.handle_stream_block(block2)

        # Block2 should initially be on the main chain
        self.assertEqual(added.chain, MAIN_CHAIN)

        added = self.chain.handle_stream_block(block3)
        # After the reconverge the newest block should be on the main chain
        self.assertEqual(added.chain, MAIN_CHAIN)

        # And it should be the tip of the main chain
        self.assertEqual(self.chain.chain_peak.hash, block3.hash)

        # After the reconverge block2 should be on a sidechain
        self.assertNotEqual(self.chain.db.get_block(block2.hash), MAIN_CHAIN)

        self.assertEqual(self.chain.num_convergences, 1)

        self.assertEqual(len(self.chain.db.block_cache), 2)

    def test_fork_grow_no_reconverge(self):
        stream = open(self.chain.blk_files[0], 'r')

        # Mock reconverge method
        self.chain.reconverge = MagicMock()

        # Add one block
        block1 = self.chain.handle_stream_block(BlockFactory.from_stream(stream)['block'])

        # Add 10 blocks to the main chain
        for i in range(10):
            self.chain.handle_stream_block(BlockFactory.from_stream(stream)['block'])

        # simulate fork
        block2 = BlockFactory.from_stream(stream)['block']
        block2.previousblockhash = block1.hash
        added = self.chain.handle_stream_block(block2)
        # make sure its not on the main chain
        self.assertNotEqual(added.chain, MAIN_CHAIN)

        self.chain.db.update_block = MagicMock()

        # simulate fork grow
        block3 = BlockFactory.from_stream(stream)['block']
        block3.previousblockhash = block2.hash
        added = self.chain.handle_stream_block(block3)
        # check if it belongs to the same sidechain as block2
        self.assertEqual(added.chain, block2.chain)

        self.assertTrue(self.chain.db.update_block.called)

        # Reconverge shouldn't be called
        self.assertFalse(self.chain.reconverge.called)

    def test_fork_grow_reconverge(self):
        stream = open(self.chain.blk_files[0], 'r')

        # Add one block
        block1 = self.chain.handle_stream_block(BlockFactory.from_stream(stream)['block'])

        # Add the second block (we'll use it to check if reconverge worked)
        block2 = self.chain.handle_stream_block(BlockFactory.from_stream(stream)['block'])

        # Make sure it's initially on the main chain
        self.assertEqual(block2.chain, MAIN_CHAIN)

        # Add 10 blocks to the main chain
        for i in range(10):
            self.chain.handle_stream_block(BlockFactory.from_stream(stream)['block'])

        # Simulate fork on block1
        block3 = BlockFactory.from_stream(stream)['block']
        block3.previousblockhash = block1.hash
        added = self.chain.handle_stream_block(block3)
        self.assertNotEqual(added.chain, MAIN_CHAIN)

        # Simulate fork grow and reconverge
        block4 = BlockFactory.from_stream(stream)['block']
        block4.previousblockhash = block3.hash
        block4.work += 10000000
        added = self.chain.handle_stream_block(block4)

        # After the reconverge the added block should be on the main chain
        self.assertEqual(added.chain, MAIN_CHAIN)
        # And it should be the tip of the main chain
        self.assertEqual(added.hash, self.chain.chain_peak.hash)
        # Block2 should not be on the main chain any more
        self.assertNotEqual(self.chain.db.get_block(block2.hash).chain, MAIN_CHAIN)


class StartRpcSyncAfterStreamSync(unittest.TestCase):
    """
    Stream sync reached the limit, RPC sync should start
    """
    def setUp(self):
        self.db = MagicMock()

        self.example_block = BlockFactory.from_mongo(EXAMPLE_MONGO_BLOCK)
        self.db.blocks.find_one = MagicMock(return_value=EXAMPLE_MONGO_BLOCK)
        self.chain = ExploderSyncer(
            database=self.db,
            blocks_dir="/home/vagrant/.gamecredits/blocks/",
            rpc_client=MagicMock()
        )
        self.db.blocks.create_index = MagicMock()
        self.SYNC_LIMIT = 100

    def test_rpc_sync_no_reconverge(self):
        self.chain.db.highest_block = PropertyMock(return_value=self.example_block)
        self.chain._get_rpc_block_by_hash = MagicMock(return_value=self.example_block)
        self.chain.db.flush_cache = MagicMock()
        self.chain._follow_chain_and_insert = MagicMock()
        self.chain._find_reconverge_point = MagicMock(return_value=(self.example_block, self.example_block))
        self.chain._follow_chain_and_delete = MagicMock()
        self.chain._sync_rpc(550, 50)

        self.assertTrue(self.chain._follow_chain_and_insert.called)

        # There should be no reconverge
        self.assertFalse(self.chain._find_reconverge_point.called)
        # No blocks should be deleted
        self.assertFalse(self.chain._follow_chain_and_delete.called)

        self.assertTrue(self.chain.db.flush_cache.called)

    def test_rpc_sync_reconverge(self):
        self.chain.highest_block = PropertyMock(return_value=self.example_block)
        block2 = copy.deepcopy(self.example_block)
        block2.previousblockhash = "somethingsomething"
        self.chain._get_rpc_block_by_hash = MagicMock(return_value=block2)

        reconverge_mock = MagicMock(return_value=(self.example_block, self.example_block))

        self.chain._find_reconverge_point = reconverge_mock
        self.chain._follow_chain_and_delete = MagicMock()
        self.chain._follow_chain_and_insert = MagicMock()

        self.chain._sync_rpc(550, 50)

        self.assertTrue(self.chain._find_reconverge_point.called)


if __name__ == '__main__':
    unittest.main()
