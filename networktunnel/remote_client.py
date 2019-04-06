from twisted.internet import protocol

from networktunnel.helpers import create_udp_frame, parse_udp_frame
from networktunnel.logger import LogMixin


class ProxyClient(protocol.Protocol, LogMixin):

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
        if self.server is not None and self.server.transport:
            self.server.transport.loseConnection()
            self.server = None

    def dataReceived(self, data):
        self.server.write(data)  # 转发数据

    def write(self, data):
        self.transport.write(data)


class BindProxyClient(protocol.Protocol, LogMixin):
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

        self.on_bind_connect_success()

    def connectionLost(self, reason):
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())
        if self.server is not None and self.server.transport:
            self.server.transport.loseConnection()
            self.server = None

    def dataReceived(self, data):
        self.server.write(data)

    def write(self, data):
        self.transport.write(data)


class UdpProxyClient(protocol.DatagramProtocol, LogMixin):
    def __init__(self, server, addr, atyp):
        self.server = server
        self.server.client = self

        self.origin_addr = addr
        self.origin_atyp = atyp
        self.host_address = None

        self.allowed_address = {
            self.origin_addr: self.origin_atyp
        }

    def startProtocol(self):
        self.host_address = self.transport.getHost()

    def datagramReceived(self, data, addr):
        if addr not in self.allowed_address:
            return

        if addr == self.origin_addr:
            self.receive_from_origin(data)
        else:
            self.receive_from_target(data, addr)

    def receive_from_target(self, data, addr):
        # 封包 -> 发往客户端, data 未加密
        host, port = addr
        atyp = self.allowed_address.get(addr)

        data = create_udp_frame(0, atyp, host, port, data)

        # todo 加密
        self.transport.write(data, self.origin_addr)

    def receive_from_origin(self, data):
        # todo 首先解密
        # 解包 -> 发往目标服务器
        frag, atyp, host, port, buff = parse_udp_frame(data)

        remote_addr = (host, port)

        if remote_addr not in self.allowed_address:
            self.allowed_address.update(remote_addr=atyp)

        if frag != 0:
            # todo 分片
            return  # 这里直接丢弃

        # 不加密直接发给目标服务器
        self.transport.write(data, remote_addr)

    def connectionRefused(self):
        # 如果没有服务器监听我们发送到的地址，则调用。
        pass


class BindProxyClientFactory(protocol.ServerFactory):

    def __init__(self, server):
        self.server = server

    def buildProtocol(self, addr):
        return BindProxyClient(self, self.server)
