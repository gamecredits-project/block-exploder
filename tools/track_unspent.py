import threading
import pymongo
from pymongo import MongoClient
import time


class TransactionThread(threading.Thread):
    def __init__(self, threadID, name, transactions, interval):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.transactions = transactions
        self.interval = interval

    def run(self):
        print "Starting " + self.name

        trs = self.transactions.find(
            {"blocktime": {"$gte": self.interval[0], "$lte": self.interval[1]}}
        )

        for tr in trs:
            for vout_index, vout in enumerate(tr['vout']):
                spend = self.transactions.find_one({
                    "vin.prev_txid": tr['txid'],
                    "vin.vout_index": vout_index
                })

                if not spend:
                    self.transactions.update(
                        {
                            '_id': tr['_id']
                        },
                        {
                            '$set': {
                                'vout.%s.spent' % vout_index: False
                            }
                        },
                        multi=False
                    )

        print "Exiting " + self.name


if __name__ == '__main__':
    client = MongoClient()
    db = client.exploder

    num_threads = 16
    num_transactions = db.transactions.count()
    trs_per_thread = num_transactions / num_threads

    print ("Total trs: %s, trs per thread: %s" % (num_transactions, trs_per_thread))

    vertices = []
    offset = 0
    for i in range(num_threads):
        blocktime = db.transactions.find().sort("blocktime", pymongo.ASCENDING)\
            .skip(offset).limit(1).next()['blocktime']
        vertices.append(blocktime)
        offset += trs_per_thread

    max_blocktime = db.transactions.find().sort("blocktime", pymongo.DESCENDING)\
        .limit(1).next()['blocktime']

    vertices.append(max_blocktime)

    intervals = []
    # Make intervals
    for i in range(len(vertices) - 1):
        intervals.append((vertices[i], vertices[i + 1]))

    print intervals

    start = time.time()

    threads = []
    for i in range(len(intervals)):
        thread = TransactionThread(i, "Thread-%s" % i, db.transactions, intervals[i])
        threads.append(thread)

    [thr.start() for thr in threads]
    [thr.join() for thr in threads]

    end = time.time()

    print "Transaction output marking complete. Duration: %s seconds" % (end - start)
