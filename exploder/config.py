import os


class Development(object):
    DEBUG = bool(os.environ["FLASK_DEBUG"])
    RPC_USER = os.environ["RPC_USER"]
    RPC_PASSWORD = os.environ["RPC_PASSWORD"]
    DATADIR_PATH = os.environ["DATADIR_PATH"]
