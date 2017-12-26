import unittest
import sys
import os
from flask import Flask
from flask_socketio import SocketIO, emit
from mock import Mock, patch
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# sys.path.append('..')
from socket_transmitter import block_buffer, first_block_from_buffer, tx_buffer
import initiated_values as iv
import json

app = Flask(__name__)
socketio = SocketIO(app)


# This is a custom event where we check if the client is connected to the block socket
@socketio.on('block_connected', namespace='/block')
def block_connected_test():
    # User should receive 'Block Socket Connected Successfully!' message
    emit('block_connected_message', 'Block Socket Connected Successfully!', namespace='/block')


# This is a custom event where we check if the client is connected to the transaction socket
@socketio.on('tx_connected', namespace='/tx')
def tx_connected_test():
    # User should receive 'Tx Socket Connected Successfully!' message
    emit('tx_connected_message', 'Tx Socket Connected Successfully!', namespace='/tx')

@socketio.on('background_mock_block_sender_with_difference', namespace='/block')
def block_mock_data_with_difference_test():
    # difference_between_blocks = int(check_difference_between_blocks(first_block_from_buffer(mock_block_height()) - iv.CURRENT_BLOCK))
    # difference_between_blocks = first_block_from_buffer(mock_block_height()) - iv.CURRENT_BLOCK
    difference_between_blocks = int(check_difference_between_blocks_true())
    if difference_between_blocks > 0:
        testing_difference_between_blocks(difference_between_blocks)
    socket_wait()

def check_difference_between_blocks_true():
    return first_block_from_buffer(mock_block_height()) - iv.CURRENT_BLOCK
    # return difference

def check_difference_between_blocks_false():
    value_is_zero = 0
    return value_is_zero

@socketio.on('background_mock_block_sender_with_no_difference', namespace='/block')
def block_mock_data_no_difference_test():
    # difference_between_blocks = 0
    difference_between_blocks = int(check_difference_between_blocks_false()) - 1
    # difference_between_blocks = int(check_difference_between_blocks(0))
    if difference_between_blocks > 0:
        testing_difference_between_blocks(difference_between_blocks)
    socket_wait()

@pytest.fixture
def testing_difference_between_blocks(difference_between_blocks):
    iv.CURRENT_BLOCK = first_block_from_buffer(mock_block_height())
    while difference_between_blocks > 0:
        # iv.NUMBER_OF_TX_IN_BLOCK += len(
        #     block_buffer(mock_block_height())[-1 + difference_between_blocks]['tx'])
        json_block_data = block_buffer(mock_block_height())[
            -1 + difference_between_blocks]
        # block_mock_data = Mock(return_value=json_block_data)
        # block_mock_data(json_block_data)

        # block_mock_data.return_value
        emit('block_mock_data', json_block_data, namespace='/block')

        difference_between_blocks -= 1


def socket_wait():
    # This method should be called either when there is a new block or there isn't
    socketio.sleep(0)


def mock_block_height():
    # This method is used to read some dummy data about blocks
    json_file = os.path.dirname(os.path.abspath(__file__)) + '/block.json'
    with open(json_file) as data_file:
        data = json.load(data_file)
    return data


class TestSocketIO(unittest.TestCase):
    iv.CURRENT_BLOCK = mock_block_height()[-1]['height']

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_block_connection(self):
        client = socketio.test_client(app, namespace='/block')
        client.get_received('/block')
        client.emit('block_connected', namespace='/block')
        received = client.get_received('/block')
        expected_data = ['Block Socket Connected Successfully!']

        self.assertEqual(received[0]['args'], expected_data)

    def test_tx_connection(self):
        client = socketio.test_client(app, namespace='/tx')
        client.get_received('/tx')
        client.emit('tx_connected', namespace='/tx')
        received = client.get_received('/tx')
        expected_data = ['Tx Socket Connected Successfully!']

        self.assertEqual(received[0]['args'], expected_data)

    def test_block_difference(self):
        # Here we are creating a test_client so we can receive data from the /block socket
        client = socketio.test_client(app, namespace='/block')
        client.get_received('/block')
        client.emit('background_mock_block_sender_with_difference', namespace='/block')
        actual_result = client.get_received('/block')

        # Here we have to instance this mock method
        # mock_check_difference_between_blocks_true()

        # mock_real_return_value = mock_block_data.return_value[:-1]
        # mock_block_data = Mock()
        # mock_block_data()

        # Here we check if the check_difference_between_blocks_true is called
        # self.assertTrue(mock_check_difference_between_blocks_true.called)
        # self.assertFalse(mock_check_difference_between_blocks_false.called)

        # Here we check if the data we received is not None
        self.assertIsNotNone(actual_result)

        # Here we are checking is our emit data really a list data structure
        test_data_is_list = isinstance(actual_result, list)
        self.assertTrue(test_data_is_list)

    def test_no_block_difference(self):
        client = socketio.test_client(app, namespace='/block')
        client.get_received('/block')
        client.emit('background_mock_block_sender_with_no_difference', namespace='/block')
        actual_result = client.get_received('/block')

        # Here we have to instance this mock method
        # mock_check_difference_between_blocks_false()
        # mock_check_difference_between_blocks_true()

        # Here we check if the check_difference_between_blocks_false is called
        # self.assertTrue(mock_check_difference_between_blocks_false.called)
        # self.assertFalse(mock_check_difference_between_blocks_true.called)
        expected_result = []

        # self.assertFalse(mock.called)
        self.assertEqual(actual_result, expected_result)


if __name__ == "__main__":
    unittest.main()
