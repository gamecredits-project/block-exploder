import unittest
import requests
import json


class BlocksTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1/api/"

    def test_get_latest_blocks(self):
        params = {
            "limit": 10,
            "offset": 3
        }
        result = requests.get(self.url + "blocks/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)

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
        cls.url = "http://127.0.0.1/api/"

    def test_get_latest_transactions(self):
        params = {
            "limit": 10,
            "offset": 1
        }
        result = requests.get(self.url + "transactions/latest", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)

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
        cls.url = "http://127.0.0.1/api/"

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


class NetworkTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1/api/"

    def test_get_hashrates(self):
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

    def test_get_usd_price(self):
        result = requests.get(self.url + "network/price")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)


class ClientTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1/api/"

    def test_get_latest_sync_history(self):
        params = {
            "limit": 2
        }
        result = requests.get(self.url + "client/sync_history", params)
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(len(data), 2)

    def test_get_client_info(self):
        result = requests.get(self.url + "client/info")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)


class SearchTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.url = "http://127.0.0.1/api/"

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

    def test_invalid_search(self):
        result = requests.get(self.url + "search/" + "blabla")
        self.assertEquals(result.status_code, 200)
        self.assertTrue(result.text)
        data = json.loads(result.text)
        self.assertEquals(data["searchBy"], "blabla")
        self.assertFalse(data["type"])


if __name__ == "__main__":
    unittest.main()
