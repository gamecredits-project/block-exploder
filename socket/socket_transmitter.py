import helpers as helpp
import config as conf
import initiated_values as iv

iv.CURRENT_BLOCK = helpp.get_latest_five_blocks()[-1]['height']
# For dev mode uncomment line bellow, it will call last 4 block and its transactions
# Instead of waiting for new block to be created
# iv.CURRENT_BLOCK = helpp.get_latest_five_blocks()[-1]['height']


def block_buffer(url):
    array_of_blocks = []
    del array_of_blocks[:]
    array_of_blocks.extend(url)
    return array_of_blocks


def first_block_from_buffer(url_from_block_buffer):
    block_height = block_buffer(url_from_block_buffer)[0]['height']
    return block_height


def get_differences_between_blocks(difference_between_blocks):
    iv.CURRENT_BLOCK = first_block_from_buffer(helpp.get_latest_five_blocks())
    while difference_between_blocks > 0:
        print("Current number tx in block: {}".format(iv.NUMBER_OF_TX_IN_BLOCK))

        iv.NUMBER_OF_TX_IN_BLOCK += len(
            block_buffer(helpp.get_latest_five_blocks())[-1 + difference_between_blocks]['tx'])
        conf.socketio.emit('background_block_sender',
                           {'latest_block_data': block_buffer(helpp.get_latest_five_blocks())[
                               -1 + difference_between_blocks]},
                           namespace='/block')

        difference_between_blocks -= 1



def emit_new_blocks():
    difference_between_blocks = first_block_from_buffer(helpp.get_latest_five_blocks()) - iv.CURRENT_BLOCK

    if difference_between_blocks > 0:
        get_differences_between_blocks(difference_between_blocks)


def block_background_thread():
    while True:
        emit_new_blocks()
        conf.socketio.sleep(conf.BLOCK_THREAD_SLEEP)


def tx_buffer(url):
    array_of_tx = []
    del array_of_tx[:]
    array_of_tx.extend(helpp.get_latest_transactions(url + str(iv.NUMBER_OF_TX_IN_BLOCK)))
    return array_of_tx


def emit_new_tx():
    print("Info about tx's in block {}".format(iv.NUMBER_OF_TX_IN_BLOCK))

    if iv.NUMBER_OF_TX_IN_BLOCK > 0:
        tx_buffer(conf.LATEST_N_TX_URL)
        for tx in tx_buffer(conf.LATEST_N_TX_URL):
            conf.socketio.emit('background_tx_sender', {'latest_tx_data': tx}, namespace='/tx')
            conf.socketio.sleep(1)
        iv.NUMBER_OF_TX_IN_BLOCK = 0


def tx_background_thread():
    while True:
        emit_new_tx()
        conf.socketio.sleep(conf.BLOCK_THREAD_SLEEP)
