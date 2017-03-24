import click
import os

from tree import ChainTree
from helpers import has_length
from classes import ParsedBlock
from pymongo import MongoClient
from factories import BlockFactory, VoutFactory, VinFactory


RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"


class BlockchainParser(object):
    def __init__(self, path, limit):
        self.path = path
        self.limit = limit
        self.filepos = None

        self.mongo = MongoClient()

        self.exploder_db = self.mongo.exploder

        self.blocks = self.exploder_db.blocks
        self.transactions = self.exploder_db.transactions
        self.vin = self.exploder_db.vin
        self.vout = self.exploder_db.vout
        self.addresses = self.exploder_db.addresses

        if os.path.isdir(self.path):
            self.blk_files = sorted(
                [os.path.join(self.path, f) for f in os.listdir(self.path) if self.is_block_file(f)]
            )
        elif os.path.isfile(self.path):
            self.blk_files = [self.path]
        else:
            raise Exception("Given path is not a blk.dat file or a block directory")

        # Chain tree with references to the DB
        self.chain_tree = ChainTree(block_db=self.blocks, tr_db=self.transactions, vin_db=self.vin, vout_db=self.vout)

    def is_block_file(self, path):
        return path[-4:] == '.dat' and path[:3] == 'blk'

    @property
    def parsed_blocks(self):
        parsed = 0

        for f in self.blk_files:
            dat = open(f, 'r')

            while has_length(dat, 80) and (self.limit == 0 or parsed < self.limit):
                if self.filepos is not None:
                    dat.seek(self.filepos)

                block = ParsedBlock(dat)

                node = self.chain_tree.add_block(block)
                
                # # Add a block

                block.chainwork = node.chainwork
                block.height = node.height

                # mongo_block = block_factory.parsed_to_dict(block)

                # block_batch.append(mongo_block)

                # for tr in block.tx:
                #     tr_batch.append(tr.to_dict())

                #     for vin in tr.vin:
                #         vin_batch.append(vin_factory.parsed_to_mongo(vin, tr.txid))

                #     for (i, vout) in enumerate(tr.vout):
                #         vout_batch += vout_factory.parsed_to_mongo(vout, tr.txid, i)

                # if parsed % 1000 == 0:
                #     self.blocks.insert_many(block_batch)
                #     self.transactions.insert_many(tr_batch)
                #     self.vin.insert_many(vin_batch)
                #     self.vout.insert_many(vout_batch)
                #     block_batch = []
                #     tr_batch = []
                #     vin_batch = []
                #     vout_batch = []

                # self.filepos = dat.tell()

                # if not has_length(dat, 80):
                #     self.filepos = 0

                parsed += 1

                yield block

    def __str__(self):
        return "<BlockchainParser: path=%s, limit=%s>" % (self.path, self.limit)


import json 
from pprint import pprint

@click.command()
@click.argument('address')
def unspent(address):
    mongo = MongoClient()
    outs = mongo.exploder.vout.find({"address": address})

    unspent = []
    for out in outs:
        spend = mongo.exploder.vin.find_one({"txid": out['txid'], "vout": out['index']})

        if spend:
            pprint(spend)

    print unspent


@click.command()
@click.option('--limit', default=0, help='Limit number of blocks to parse')
@click.argument('path')
def parse(path, limit):
    parser = BlockchainParser(path, limit)

    for block in parser.parsed_blocks:
        if block.height % 1000 == 0:
            print "Progress: %s%%, height: %s" % ((block.height * 100 / float(1618712)), block.height)


@click.command()
def drop():
    mongo = MongoClient()

    answer = None
    while answer not in ['y', 'n']:
        answer = raw_input('Are you sure you want to drop all collections from the DB? [y/n] ').lower()

        if answer == 'y':
            mongo.exploder.blocks.drop()
            mongo.exploder.transactions.drop()
            mongo.exploder.vin.drop()
            mongo.exploder.vout.drop()
            print("Collections dropped.")


@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli.add_command(parse)
    cli.add_command(drop)
    cli.add_command(unspent)
    cli()
