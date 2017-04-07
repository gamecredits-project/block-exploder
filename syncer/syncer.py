import click
import time
import sys

from interactors import ExploderSyncer
from pymongo import MongoClient
from bitcoinrpc.authproxy import AuthServiceProxy
from gateways import DatabaseGateway
import pymongo

RPC_USER = "62ca2d89-6d4a-44bd-8334-fa63ce26a1a3"
RPC_PASSWORD = "CsNa2vGB7b6BWUzN7ibfGuHbNBC1UJYZvXoebtTt1eup"


@click.command()
def create_indexes():
    mongo = MongoClient()
    db = mongo.exploder
    db.vout.create_index([("address", pymongo.HASHED)])
    db.vin.create_index([("prev_txid", pymongo.HASHED)])
    db.vin.create_index([("vout_index", pymongo.ASCENDING)])
    db.transactions.create_index([("blockhash", pymongo.ASCENDING)])


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


@click.command()
@click.argument('path')
def listen(path):
    mongo = MongoClient()
    rpc = AuthServiceProxy("http://%s:%s@127.0.0.1:8332"
                           % (RPC_USER, RPC_PASSWORD))
    db = DatabaseGateway(database=mongo.exploder)
    syncer = ExploderSyncer(database=db, blocks_dir=path, rpc_client=rpc, rpc_sync_percent=98)

    while True:
        time.sleep(5)
        if rpc.getblockcount() > db.highest_block.height:
            syncer.sync()
            sys.stdout.flush()


@click.group()
def cli():
    pass


if __name__ == "__main__":
    cli.add_command(drop)
    cli.add_command(create_indexes)
    cli.add_command(listen)
    cli()
