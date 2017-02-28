from exploder import chain
import sys


def profile_sync(num):
    chain.sync(limit=num)


def profile_get_latest_blocks(num):
    if num:
        chain.get_latest_blocks(num)
    else:
        chain.get_latest_blocks(5)


def profile_get_block_by_hash(hash):
    chain._get_block_by_hash(hash)


def profile_get_block_transactions(hash):
    block = chain.get_block(hash)
    chain.get_block_transactions_2(block)


def profile_get_latest_transactions(num):
    chain.get_latest_transactions(num)


if __name__ == "__main__":
    # profile()
    argument = None

    if len(sys.argv) > 1:
        argument = sys.argv[1]

    profile_get_latest_transactions(int(argument))
