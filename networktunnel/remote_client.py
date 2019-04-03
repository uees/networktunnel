from twisted.internet import protocol

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


class RemoteTCPClientFactory(protocol.ClientFactory):
    protocol = RemoteTCPClient

    def __init__(self, server):
        self.server = server

    def clientConnectionFailed(self, connector, reason):
        self.server.transport.loseConnection()


class RemoteBindClient(protocol.Protocol, LogMixin):
    def __init__(self, server):
        self.server = server

    def connectionMade(self):
        self.factory.num_protocols += 1

    def connectionLost(self, reason):
        if self.factory.num_protocols > 0:
            self.factory.num_protocols -= 1

    def dataReceived(self, data):
        self.transport.write(data)


class RemoteBindClientFactory(protocol.ServerFactory):
    protocol = RemoteBindClient

    def __init__(self, server):
        self.server = server
        self.reactor = server.factory.reactor
        self.num_protocols = 0


class RemoteUdpClient(protocol.Protocol, LogMixin):
    pass
