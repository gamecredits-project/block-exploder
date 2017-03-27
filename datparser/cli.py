import click

from parser import Blockchain
from pymongo import MongoClient
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
    mongo = MongoClient()
    chain = Blockchain(mongo.exploder, path)
    chain.sync(limit)


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
