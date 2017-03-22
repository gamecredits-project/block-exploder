import click
import os

from tree import ChainTree
from helpers import has_length
from classes import ParsedBlock
from pymongo import MongoClient
import json

RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"


class BlockchainParser(object):
    def __init__(self, path, limit):
        self.path = path
        self.limit = limit
        self.filepos = None

        if os.path.isdir(self.path):
            self.blk_files = sorted(
                [os.path.join(self.path, f) for f in os.listdir(self.path) if self.is_block_file(f)]
            )
        elif os.path.isfile(self.path):
            self.blk_files = [self.path]
        else:
            raise Exception("Given path is not a blk.dat file or a block directory")

        self.chain_tree = ChainTree()

        self.mongo = MongoClient()

        self.exploder_db = self.mongo.exploder

        self.blocks = self.exploder_db.blocks
        self.transactions = self.exploder_db.transactions
        self.transaction_inputs = self.exploder_db.transaction_inputs
        self.transaction_outputs = self.exploder_db.transaction_outputs
        self.addresses = self.exploder_db.addresses

    def is_block_file(self, path):
        return path[-4:] == '.dat' and path[:3] == 'blk'

    def parse_blocks(self):
        inserted = 0
        for f in self.blk_files:
            dat = open(f, 'r')

            while inserted < self.limit and has_length(dat, 80):
                if self.filepos is not None:
                    dat.seek(self.filepos)

                block = ParsedBlock(dat)

                factory = BlockFactory()

                mongo_block = factory.parsed_to_mongo_dict(block)
                block_transactions = [tr.to_dict() for tr in block.tx]


                inserted += 1


    def __str__(self):
        return "<BlockchainParser: path=%s, limit=%s>" % (self.path, self.limit)


class BlockFactory():
    def parsed_to_mongo_dict(self, parsed_block):
        txids = [tx.txid for tx in parsed_block.tx]
        block_dict = parsed_block.to_dict()
        block_dict['tx'] = txids
        return block_dict


@click.command()
@click.option('--limit', default=0, help='Limit number of blocks to parse')
@click.argument('path')
def parse(path, limit):
    parser = BlockchainParser(path, limit)
    parser.parse_blocks()


@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli.add_command(parse)
    cli()
