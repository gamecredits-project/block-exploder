import redis
import os
import requests
from zipfile import ZipFile


REDIS_CLIENT = redis.Redis()


def only_one(function=None, key="", timeout=None):
    """Enforce only one celery task at a time."""

    def _dec(run_func):
        """Decorator."""

        def _caller(*args, **kwargs):
            """Caller."""
            ret_value = None
            have_lock = False
            lock = REDIS_CLIENT.lock(key, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = run_func(*args, **kwargs)
            finally:
                if have_lock:
                    lock.release()

            return ret_value

        return _caller

    return _dec(function) if function is not None else _dec


def generate_bootstrap(datadir_path, output_directory):
    """
    Generates bootstrap file from blockfiles in the datadir
    """
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    blocks_path = os.path.join(datadir_path, 'blocks')

    # Find block files
    blockfiles = [f for f in os.listdir(blocks_path) if _is_block_file(f)]

    # Load them all into memory
    data = ""
    for path in blockfiles:
        f = open(os.path.join(blocks_path, path), 'r')
        data += f.read()
        f.close()

    # Write them to the output file
    with open(os.path.join(output_directory, 'bootstrap.dat'), 'w') as out:
        out.write(data)

    # Compress (zip) the bootstrap file
    # Instead of os.path.basename the following code could be used: arcname='bootstrap.dat'
    # arcname='bootstrap.dat' creates a directory that is named after the zip file
    with ZipFile(os.path.join(output_directory, 'bootstrap.zip'), 'w') as myzip:
        myzip.write(os.path.join(output_directory, 'bootstrap.dat'), os.path.basename('bootstrap.dat'))



def _is_block_file(filename):
    """
    Checks if the provided filename is a block file
    """
    return filename[:3] == 'blk' and filename[-3:] == 'dat'


def get_client_ip(url):
    """
    Returns server's ip

    @param url: Link for api that returns your ip
    @type url: string
    @return: This server's ip if successful, otherwise None
    @rtype: string
    """
    try:
        param = {
            "format": "json"
        }
        res = requests.get(url, params=param)
        json_data = res.json()
        return json_data['ip']
    except requests.exceptions.RequestException:
        return None
