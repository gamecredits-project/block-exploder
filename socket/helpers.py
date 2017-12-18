import requests as req
import json
import config as conf


def get_latest_five_blocks():
    res = req.get(conf.LATEST_FIVE_BLOCKS_URL)
    five_blocks = res.json()

    return five_blocks

def get_latest_transactions(url):
    res = req.get(url)
    transactions = res.json()

    return transactions

def get_latest_price_stats():
    res = req.get(conf.LATEST_PRICE_STATS_URL)
    price_stats = res.json()

    return price_stats

# get_latest_price_stats()