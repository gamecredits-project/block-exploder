import os


def calculate_blockchain_size_in_gb(datadir_path):
    """
    Walks (recursively) through the provided data directory
    and calculates the size of the whole directory
    """
    size = 0
    for root, dirs, files in os.walk(datadir_path):
        for file in files:
            size += os.stat(os.path.join(root, file)).st_size

    # Calculate size in GB
    B_IN_GB = pow(2, 30)
    size = float(size) / B_IN_GB
    return round(size, 2)


def generate_bootstrap(datadir_path, output_path):
    """
    Generates bootstrap file from blockfiles in the datadir
    """
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
    with open(output_path, 'w') as out:
        out.write(data)


def _is_block_file(filename):
    """
    Checks if the provided filename is a block file
    """
    return filename[:3] == 'blk' and filename[-3:] == 'dat'


if __name__ == '__main__':
    print "Blockchain size: %sGB" % calculate_blockchain_size_in_gb('/home/vagrant/.gamecredits')
    generate_bootstrap('/home/vagrant/.gamecredits', '/home/vagrant/bootstrap.dat')
