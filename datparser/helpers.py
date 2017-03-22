import struct
import binascii
import hashlib


def uint1(stream):
    return ord(stream.read(1))


def uint2(stream):
    return struct.unpack('H', stream.read(2))[0]


def uint4(stream):
    return struct.unpack('I', stream.read(4))[0]


def uint8(stream):
    return struct.unpack('Q', stream.read(8))[0]


def hash32(stream):
    return binascii.hexlify(stream.read(32)[::-1])


def varint(stream):
    size = uint1(stream)

    if size < 0xfd:
        return size

    if size == 0xfd:
        return uint2(stream)

    if size == 0xfe:
        return uint4(stream)

    if size == 0xff:
        return uint8(stream)

    return -1


def has_length(stream, size):
    curPos = stream.tell()
    stream.seek(0, 2)

    fileSize = stream.tell()
    stream.seek(curPos)

    tempBlockSize = fileSize - curPos

    if tempBlockSize < size:
        return False
    return True


def double_sha(input_bytes, reverse=False):
    hash = hashlib.sha256(hashlib.sha256(input_bytes).digest()).digest()

    if reverse:
        hash = hash[::-1]

    return binascii.hexlify(hash)
