from db import Blockchain
import pickle

chain = Blockchain("...")


def get_example_addresses(num):
    counter = 0
    for (key, val) in chain.address_db:
        print(pickle.loads(val))
        counter += 1
        if counter >= num:
            break
