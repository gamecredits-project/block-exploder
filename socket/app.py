import logging
import config as conf
import initiated_values as iv
import socket_transmitter as st
from flask import render_template


# opcija za logovanje samo gresaka, iskljucivanje logovanja zahteva
LOG = logging.getLogger('werkzeug')
LOG.setLevel(logging.ERROR)


@conf.app.route('/socket.io')
def index():
    return render_template('index.html', async_mode=conf.socketio.async_mode)


@conf.socketio.on('disconnect_block', namespace='/block')
def disconnect_block():
    conf.disconnect()

@conf.socketio.on('disconnect_tx', namespace='/tx')
def disconnect_tx():
    print("Diskonektovan je")
    conf.disconnect()


@conf.socketio.on('block_connected', namespace='/block')
def block_connect():
    if iv.THREAD_BLOCK is None:
        iv.THREAD_BLOCK = conf.socketio.start_background_task(target=st.block_background_thread)
    conf.socketio.emit('block_response', {'block_data': 'Block connected'})
    print("Block socket is connected")


@conf.socketio.on('tx_connected', namespace='/tx')
def tx_connect():
    if iv.THREAD_TX is None:
        iv.THREAD_TX = conf.socketio.start_background_task(target=st.tx_background_thread)
    conf.socketio.emit('tx_response', {'tx_data': 'Tx connected'})
    print("Tx socket is connected")


if __name__ == '__main__':
    conf.socketio.run(conf.app, debug=False, port=5004)
