import logging
import config as conf
import initiated_values as iv
import socket_transmitter as st
from flask import render_template


# Werkzeug will log only errors
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
    conf.disconnect()

@conf.socketio.on('disconnect_price_stats', namespace='/price-stats')
def disconnect_price_stats():
    conf.disconnect()

@conf.socketio.on('block_connected', namespace='/block')
def block_connect():
    if iv.THREAD_BLOCK is None:
        iv.THREAD_BLOCK = conf.socketio.start_background_task(target=st.block_background_thread)
    conf.socketio.emit('block_response', {'block_data': 'Block connected'})

@conf.socketio.on('tx_connected', namespace='/tx')
def tx_connect():
    if iv.THREAD_TX is None:
        iv.THREAD_TX = conf.socketio.start_background_task(target=st.tx_background_thread)
    conf.socketio.emit('tx_response', {'tx_data': 'Tx connected'})

@conf.socketio.on('price_stats_connected', namespace='/price-stats')
def price_stats_connected():
    conf.socketio.start_background_task(target=st.price_stats_background_thread)
    conf.socketio.emit('price_stats_response', {'price_stats_data': 'Price Stats connected'})

if __name__ == '__main__':
    print 'BlockExplorer socket is up and running! \n'
    conf.socketio.run(conf.app, debug=False, port=5004)
