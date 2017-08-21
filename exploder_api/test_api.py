import unittest
import requests
import json
import sys


class BlocksTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_get_latest_blocks(self):
        params = {
            "limit": 10,
            "offset": 3
        }
        result = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)

    def test_get_latest_blocks_too_small_limit(self):
        params = {
            "limit": -3
        }
        res = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_blocks_too_big_limit(self):
        params = {
            "limit": 10000000000000000000
        }
        res = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_blocks_too_small_offset(self):
        params = {
            "limit": 10,
            "offset": -2
        }
        res = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_blocks_too_big_offset(self):
        params = {
            "limit": 10,
            "offset": 10000000000000000000
        }
        res = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_block_by_hash(self):
        # First find some block hash
        params = {
            "limit": 10,
        }
        result = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get that block
        block_hash = data[0]["hash"]
        res = requests.get(self.url + "blocks/" + block_hash)
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_block_by_invalid_hash(self):
        # Block by invalid hash should return 400
        res = requests.get(self.url + "blocks/invalidhash")
        self.assertEquals(res.status_code, 400)

    def test_get_block_by_height(self):
        # First find some block height
        params = {
            "limit": 10,
        }
        result = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get that block
        block_height = {
            "height": data[0]["height"]
        }
        res = requests.get(self.url + "blocks", block_height)
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_block_by_too_small_height(self):
        block_height = {
            "height": -3
        }
        res = requests.get(self.url + "blocks", block_height)
        self.assertEquals(res.status_code, 400)

    def test_get_block_by_too_big_height(self):
        block_height = {
            "height": 10000000000000000000
        }
        res = requests.get(self.url + "blocks", block_height)
        self.assertEquals(res.status_code, 400)

    def test_get_block_confirmations(self):
        # First find some block hash
        params = {
            "limit": 10,
        }
        result = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get that block
        block_hash = data[0]["hash"]
        res = requests.get(self.url + "blocks/" + block_hash + "/confirmations")
        self.assertEquals(res.status_code, 200)
        json_data = json.loads(res.text)
        self.assertGreaterEqual(json_data["confirmations"], 0)


class TransactionsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_get_latest_transactions(self):
        params = {
            "limit": 10,
            "offset": 1
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)

    def test_get_latest_transactions_too_small_limit(self):
        params = {
            "limit": -3
        }
        res = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_transactions_too_big_limit(self):
        params = {
            "limit": 10000000000000000000
        }
        res = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_transactions_too_small_offset(self):
        params = {
            "limit": 10,
            "offset": -2
        }
        res = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_transactions_too_big_offset(self):
        params = {
            "limit": 10,
            "offset": 10000000000000000000
        }
        res = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(res.status_code, 400)

    def test_get_transactions_by_blockhash(self):
        # First find some block hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get transactions from that block
        block_hash = {
            "blockhash": data[0]["blockhash"]
        }
        res = requests.get(self.url + "transactions", block_hash)
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_transaction_by_txid(self):
        # First find some txid
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get transaction with that txid
        txid = data[0]["txid"]
        res = requests.get(self.url + "transactions/" + txid)
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_transaction_by_invalid_txid(self):
        # Transaction by invalid txid should return 400
        res = requests.get(self.url + "transactions/invalidtxid")
        self.assertEquals(res.status_code, 400)

    def test_get_transaction_confirmations(self):
        # First find some txid
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get transaction with that txid
        txid = data[0]["txid"]
        res = requests.get(self.url + "transactions/" + txid + "/confirmations")
        self.assertEquals(res.status_code, 200)
        json_data = json.loads(res.text)
        self.assertGreaterEqual(json_data["confirmations"], 0)


class AddressesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_get_address(self):
        # First find some address hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get address with that hash
        hash = data[0]["vout"][0]["addresses"][0]
        res = requests.get(self.url + "addresses/" + hash)
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_address_by_invalid_hash(self):
        # Addresses by invalid hash should return 400
        res = requests.get(self.url + "addresses/invalidhash")
        self.assertEquals(res.status_code, 400)

    def test_get_address_start_too_big(self):
        # First find some address hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get address with that hash
        hash = data[0]["vout"][0]["addresses"][0]
        param = {
            "start": 10000000000000000000
        }
        res = requests.get(self.url + "addresses/" + hash, param)
        self.assertEquals(res.status_code, 400)

    def test_get_address_start_too_small(self):
        # First find some address hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get address with that hash
        hash = data[0]["vout"][0]["addresses"][0]
        param = {
            "start": -3
        }
        res = requests.get(self.url + "addresses/" + hash, param)
        self.assertEquals(res.status_code, 400)

    def test_get_address_unspent(self):
        # First find some address hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get address with that hash
        hash = data[0]["vout"][0]["addresses"][0]
        res = requests.get(self.url + "addresses/" + hash + "/unspent")
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)

    def test_get_address_volume(self):
        # First find some address hash
        params = {
            "limit": 10
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        hash = data[0]["vout"][0]["addresses"][0]
        res = requests.get(self.url + "addresses/" + hash + "/volume")
        self.assertEquals(res.status_code, 200)
        d = json.loads(res.text)
        self.assertEquals(d["address"], hash)
        self.assertTrue(isinstance(d["volume"], (int, float)))

    def test_get_address_volume_for_unused_address(self):
        # Volume for unused address should be 0
        unused = "GVukVukVukeHjpNa1kRPydyW7TzAXhW4ud"
        res = requests.get(self.url + "addresses/" + unused + "/volume")
        self.assertEquals(res.status_code, 200)
        self.assertTrue(res.text)
        d = json.loads(res.text)
        self.assertEquals(d["address"], unused)
        self.assertEquals(int(d["volume"]), 0)

    def test_get_address_balance(self):
        # First find some address hash
        params = {
            "limit": 2
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        hash = data[0]["vout"][0]["addresses"][0]
        res = requests.get(self.url + "addresses/" + hash + "/balance")
        self.assertEquals(res.status_code, 200)
        d = json.loads(res.text)
        self.assertEquals(d["address"], hash)
        self.assertTrue(isinstance(d["balance"], (int, float)))

    def test_get_address_transaction_count(self):
        # First find some address hash
        params = {
            "limit": 2
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        hash = data[0]["vout"][0]["addresses"][0]
        res = requests.get(self.url + "addresses/" + hash + "/transaction-count")
        self.assertEquals(res.status_code, 200)
        d = json.loads(res.text)
        self.assertEquals(d["address"], hash)
        self.assertTrue(isinstance(d["transactionCount"], int))


class NetworkTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_get_network_hashrates(self):
        params = {
            "limit": 5
        }
        result = requests.get(self.url + "network/hashrates", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(len(data), 5)

    def test_get_network_info(self):
        result = requests.get(self.url + "network/info")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertTrue(data)

    def test_get_netowrk_price(self):
        result = requests.get(self.url + "network/price")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)

    def test_get_network_bootstrap(self):
        pass


class ClientTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_get_latest_sync_history(self):
        params = {
            "limit": 2
        }
        result = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(len(data), 2)

    def test_get_latest_sync_history_too_small_limit(self):
        params = {
            "limit": -3
        }
        res = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_sync_history_too_big_limit(self):
        params = {
            "limit": 10000000000000000000
        }
        res = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_sync_history_too_small_offset(self):
        params = {
            "limit": 10,
            "offset": -2
        }
        res = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(res.status_code, 400)

    def test_get_latest_sync_history_too_big_offset(self):
        params = {
            "limit": 10,
            "offset": 10000000000000000000
        }
        res = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(res.status_code, 400)

    def test_get_client_info(self):
        result = requests.get(self.url + "client/info")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)


class SearchTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1:8080/api/"

    def test_search(self):
        # First find some txid
        params = {
            "limit": 1
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get transaction with that txid
        txid = data[0]["txid"]
        result = requests.get(self.url + "search/" + txid)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(data["searchBy"], txid)
        self.assertEquals(data["type"], "transaction")

        params = {
            "limit": 1
        }

        result = requests.get(self.url + 'blocks/latest', params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)

        # Try to get block with that block_height
        block_height = data[0]['height']
        result = requests.get(self.url + "search/" + str(block_height))
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(data["searchBy"], str(block_height))
        self.assertEquals(data["type"], "block")


    def test_invalid_search(self):
        result = requests.get(self.url + "search/" + "blabla")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(data["searchBy"], "blabla")
        self.assertFalse(data["type"])

    def test_int_overflow_in_block_search(self):
        block_height = 1000
        if len(str(int(block_height))) <= len(str(int(sys.maxint))):
            result = requests.get(self.url + 'search/' + str(block_height))
            self.assertEquals(result.status_code, 200)
            self.assertTrue(result.text)
            data = json.loads(result.text)
            self.assertEquals(data["searchBy"], str(block_height))
            self.assertEquals(data["type"], "block")
        else:
            result = requests.get(self.url + 'search/' + str(block_height))
            data = json.loads(result.text)
            self.assertEquals(data["searchBy"], str(block_height))
            self.assertFalse(data["type"])







if __name__ == "__main__":
    unittest.main()
