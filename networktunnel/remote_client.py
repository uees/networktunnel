from twisted.internet import protocol

from . import constants
from .logger import LogMixin


class RemoteTCPClient(protocol.Protocol, LogMixin):

    def __init__(self, server):
        self.server = server
        self.server.client = self
        self.peer_address = None
        self.host_address = None

    def connectionMade(self):
        self.peer_address = self.transport.getPeer()
        self.host_address = self.transport.getHost()
        self.log('Connection made', self.peer_address)

        # Wire this and the peer transport together to enable
        # flow control (this stops connections from filling
        # this proxy memory when one side produces data at a
        # higher rate than the other can consume).
        self.transport.registerProducer(self.server.transport, True)
        self.server.transport.registerProducer(self.transport, True)

        # For FAST transfer
        # self.server.dataReceived, self.dataReceived = self.write, self.server.write

        self.log(f'Connect ok to {self.peer_address} request from {self.server.transport.getPeer()}')

    def connectionLost(self, reason):
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())
        self.server.client = None
        self.server.transport.loseConnection()

    def dataReceived(self, data):
        self.server.write(data)  # 转发数据

    def write(self, data):
        self.transport.write(data)


class RemoteBindProxyClient(protocol.Protocol, LogMixin):
    def __init__(self, factory, server):
        self.factory = factory
        self.server = server
        self.server.client = self
        self.peer_address = None
        self.host_address = None

    def connectionMade(self):
        self.peer_address = self.transport.getPeer()
        self.host_address = self.transport.getHost()
        self.log(f'wait connect from {self.peer_address}')

        self.transport.registerProducer(self.server.transport, True)
        self.server.transport.registerProducer(self.transport, True)

        self.server.transport.resumeProducing()

        # 第二个回复在预期的传入连接成功或失败之后发生
        self.server.make_reply(constants.SOCKS5_GRANTED, address=self.peer_address)

    def connectionLost(self, reason):
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())
        self.server.client = None
        self.server.transport.loseConnection()

    def dataReceived(self, data):
        self.server.write(data)

    def write(self, data):
        self.transport.write(data)


class RemoteUdpClient(protocol.Protocol, LogMixin):
    pass


class RemoteBindClientFactory(protocol.ServerFactory):

    def __init__(self, server):
        self.server = server

    def buildProtocol(self, addr):
        return RemoteBindProxyClient(self, self.server)
