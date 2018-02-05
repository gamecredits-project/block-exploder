import os
import ConfigParser
import logging

CONFIG_FILE = os.environ['EXPLODER_CONFIG']
config = ConfigParser.RawConfigParser()
config.read(CONFIG_FILE)


def validate_address(address):
    """
    Check if :address: is GameCredits address
    """
    if not isinstance(address, basestring):
        return False
    # Check if address starts with 'G' or '3'
    addr_first_char = config.get('syncer', 'game_address_starts_with')
    if not address.startswith(tuple(addr_first_char)):
        return False
    # Check if address size is valid
    min = config.getint('syncer', 'address_min_length')
    max = config.getint('syncer', 'address_max_length')
    if (len(address) < min) or (len(address) > max):
        return False
    return True

def check_if_address_post_key_is_valid(address_hash):
    """
    Check if :address_hash: has a appropriate body
    """
    
    if ('addresses' in address_hash and 'start' in address_hash) or 'addresses' in address_hash:
        return True
    else:
        return False


def validate_sha256_hash(hash):
    """
    Check if :hash: is appropriate size
    """
    if not isinstance(hash, basestring):
        return False
    if len(hash) != config.getint('syncer', 'sha256_hash_length'):
        return False
    return True

def check_parameter_if_int(parameter):
    """
    Check if :parameter: is a number
    Currently not in use
    """
    try:
        int(parameter)
        return True
    except ValueError:
        return False

def confirmations_from_rpc(rpc, block):
    confirmations = rpc.getblock(block['hash'])['confirmations']
    return confirmations
