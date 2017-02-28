#!/usr/bin/env python
from flask_script import Manager, Server
from exploder import app, chain
from pymongo import MongoClient
import time

manager = Manager(app)
server = Server(host="0.0.0.0", port=5000)

manager.add_command("runserver", server)


@manager.command
def delete_db():
    answer = raw_input("Are you sure you want to delete the blocker database? [Type Yes to proceed]")

    if answer == "Yes":
        client = MongoClient()
        client.drop_database('exploder')
    else:
        print("Unknown answer: %s" % answer)

    print("MongoDB database deleted.")


@manager.option('-n', '--num', help='Run sync every n seconds', required=True)
def run_blocker(num):
    print("Is this the real life?")
    while True:
        chain.sync()
        time.sleep(float(num))


if __name__ == "__main__":
    manager.run()
