from twisted.internet import protocol

from .logger import LogMixin
from . import constants


class RemoteTCPClient(protocol.Protocol, LogMixin):
    from .remote_server import RemoteSocksV5Server

    def __init__(self, server: RemoteSocksV5Server):
        self.server = server

    def connectionMade(self):
        peer = self.transport.getPeer()
        self.log('Connection made', peer)

        # self.transport.registerProducer(self.peer.transport, True)

        self.server.client = self

        address = self.transport.getHost()

        self.server.make_reply(constants.SOCKS5_GRANTED, address=address)

        self.log('Connect ok to "%s:%d" request from %s' % (
            peer.host, peer.port, str(self.server.transport.getPeer())
        ))

    def connectionLost(self, reason):
        self.log('Connection lost', self.transport.getPeer(), reason.getErrorMessage())
        self.server.client = None
        self.server.transport.loseConnection()

    def dataReceived(self, data):
        self.server.transport.write(data)

    def write(self, data):
        self.transport.write(data)


class RemoteClientFactory:
    pass
