import socket
from protocoin.clients import BitcoinClient

class MyBitcoinClient(BitcoinClient):
    def handle_version(self, message_header, message):
        print "VERSIOASDASJDLKAJSD"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("66.228.49.201", 8333))
client = BitcoinClient(sock)
client.handshake()
client.loop()