from flask import Flask, render_template
from flask_socketio import SocketIO, emit

BLOCK_THREAD_SLEEP = 3

ASYNC_MODE = None

LATEST_FIVE_BLOCKS_URL = 'https://blockexplorer.gamecredits.com/api/blocks/latest?limit=5'
LATEST_N_TX_URL = 'https://blockexplorer.gamecredits.com/api/transactions/latest?limit='

app = Flask(__name__)
socketio = SocketIO(app, async_mode=ASYNC_MODE)
