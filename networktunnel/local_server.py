import struct

from twisted.internet import defer, endpoints, protocol, reactor
from twisted.internet.endpoints import clientFromString, connectProtocol

from . import constants, errors
from .local_client import ProxyClient
from .logger import LogMixin


class ProxyServer(protocol.Protocol, LogMixin):
    STATE_METHODS = 0x01  # 协商认证方法
    STATE_AUTH = 0x02  # 认证中
    STATE_AUTH_SUCCESS = 0x03
    STATE_ESTABLISHED = 0x04  # 认证完成
    STATE_ERROR = 0xff

    def __init__(self):
        self.client = None
        self.udp_client = None
        self.peer_address = None
        self.host_address = None
        self.is_udp_pipe = False

        self._version = constants.SOCKS5_VER
        self._state = self.STATE_METHODS
        # self._buff = b''

    def connectionMade(self):
        self.peer_address = self.transport.getPeer()
        self.host_address = self.transport.getHost()

        self.factory.num_protocols += 1

    def connectionLost(self, reason):
        if self.factory.num_protocols > 0:
            self.factory.num_protocols -= 1

        if self.client is not None and self.client.transport:
            self.client.transport.loseConnection()

        self.client = None

        if self.udp_client is not None:
            self.udp_client.doStop()

        self.udp_client = None

    def dataReceived(self, data):
        if self.is_state(self.STATE_ESTABLISHED):
            # todo 第一条应该收到 CMD ，判断是否是 UDP 命令
            self.client.write(data)

        # elif self.is_state(self.STATE_AUTH_SUCCESS):
        #    # 验证成功，但是 client 还未创建, 临时缓存 buff
        #    # 其实这里不会有数据
        #    self._buff += data

        elif self.is_state(self.STATE_METHODS):
            self.negotiate_methods(data)

    def on_error(self, failure):
        self.set_state(self.STATE_ERROR)

        # failure.value is the exception instance responsible for this failure.
        if isinstance(failure, Exception):
            error = failure
        else:
            error = failure.value

        if isinstance(error, (errors.NoAcceptableMethods, errors.LoginAuthenticationFailed)):
            self.transport.write(struct.pack('!BB', self._version, error.code))
        else:
            if hasattr(error, 'code'):
                self.make_reply(error.code, self.host_address)
            else:
                self.transport.write(b'\xff')

        self.transport.loseConnection()

    def check_version(self, ver: int):
        if ver != self._version:
            self.log(f'Wrong version from {self.peer_address}')
            return defer.fail(errors.InvalidServerVersion())

        return defer.succeed(True)

    def negotiate_methods(self, data: bytes):
        """ 协商 methods """
        if len(data) < 3:
            return defer.fail(errors.ParsingError())

        ver, nmethods = struct.unpack('!BB', data[0:2])

        d = self.check_version(ver)

        def negotiate(ignored):
            methods = struct.unpack('!%dB' % nmethods, data[2:2 + nmethods])

            if constants.AUTH_ANONYMOUS not in methods:
                raise errors.NoAcceptableMethods()

            return self.start_client()

        d.addCallback(negotiate)

        return d

    def start_client(self):
        self.transport.pauseProducing()
        point = clientFromString(self.factory.reactor, "tcp:host=127.0.0.1:port=1080")
        d = connectProtocol(point, ProxyClient(self))

        def error(failure):
            raise errors.HostUnreachable()

        d.addErrback(error)

        return d

    def reply_auth_ok(self):
        self.set_state(self.STATE_ESTABLISHED)
        self.transport.write(struct.pack('!BB', self._version, constants.AUTH_ANONYMOUS))
        self.transport.resumeProducing()

    def is_state(self, state):
        return self._state == state

    def set_state(self, state):
        self._state = state


class ProxyFactory(protocol.Factory):
    protocol = ProxyServer

    def __init__(self, reactor, key):
        self.reactor = reactor
        self.key = key
        # self.crypto = crypt.MyCrypto(key)


endpoint = endpoints.serverFromString(reactor, "tcp:1081:interface=127.0.0.1")
endpoint.listen(ProxyFactory(reactor, "123456"))
reactor.run()
