import socket
import struct

from twisted.internet import defer, protocol
from twisted.internet.endpoints import clientFromString, connectProtocol

from . import constants, errors
from .helpers import parse_address
from .local_client import ProxyClient, UDPProxyClient
from .logger import LogMixin


class ProxyServer(protocol.Protocol, LogMixin):
    STATE_METHODS = 0x01  # 协商认证方法
    STATE_AUTH = 0x02  # 认证中
    STATE_COMMAND = 0x03  # 发送命令
    STATE_ESTABLISHED = 0x04  # 完成
    STATE_ERROR = 0xff

    def __init__(self):
        self.client = None
        self.udp_client = None
        self.udp_port = None
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

        if self.udp_port is not None:
            self.udp_port.stopListening()
            # self.udp_client.doStop()
            self.udp_port = None
            self.udp_client = None

    def dataReceived(self, data):
        # 接受 socks client 的数据
        if self.is_state(self.STATE_ESTABLISHED):
            self.client.write(data)

        elif self.is_state(self.STATE_METHODS):
            self.negotiate_methods(data).addErrback(self.on_error)

        elif self.is_state(self.STATE_COMMAND):
            # 判断是否是 UDP 命令
            self.parse_command(data).addErrback(self.on_error)

    def on_client_auth_ok(self):
        self.set_state(self.STATE_COMMAND)
        self.transport.write(struct.pack('!BB', self._version, constants.AUTH_ANONYMOUS))
        self.transport.resumeProducing()

    def on_client_established(self):
        self.set_state(self.STATE_ESTABLISHED)

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

    def parse_command(self, data: bytes):
        """ 解析命令 """
        if len(data) < 4:
            return defer.fail(errors.ParsingError())

        ver, cmd, rsv, atyp = struct.unpack('!4B', data[0:4])
        d = self.check_version(ver)

        def parse(ignored):
            """ 分配命令 """
            if cmd in (constants.CMD_CONNECT, constants.CMD_BIND):
                return data

            elif cmd == constants.CMD_UDP_ASSOCIATE:
                self.start_udp_client(atyp, data)

                address = self.udp_port.getHost()

                # 修改 CMD 包, 通知 socks 服务器由本地UPD代理客户端转发数据
                request = b''.join([
                    struct.pack('!4B', self._version, constants.CMD_UDP_ASSOCIATE, constants.RSV, constants.ATYP_IPV4),
                    b''.join([socket.inet_aton(address.host), struct.pack('!H', address.port)])
                ])

                return request

            raise errors.CommandNotSupported(f"Not implement {cmd} yet!")

        d.addCallback(parse)

        def send_command(request):
            self.client.sendCommand(request)

        d.addCallback(send_command)

        return d

    def start_udp_client(self, atyp, data):
        # 获取 socks 客户端绑定的 UDP 端口
        org_host, org_port = parse_address(atyp, data)

        self.upd_client = UDPProxyClient(self, addr=(org_host, org_port), atyp=atyp)
        self.udp_port = self.factory.reactor.listenUDP(0, self.upd_client)

    def start_client(self):
        self.transport.pauseProducing()
        # todo get socks server host port
        point = clientFromString(self.factory.reactor, "tcp:host=127.0.0.1:port=6778")
        d = connectProtocol(point, ProxyClient(self))

        def error(failure):
            raise errors.HostUnreachable()

        d.addErrback(error)

        return d

    def is_state(self, state):
        return self._state == state

    def set_state(self, state):
        self._state = state


class ProxyFactory(protocol.Factory):
    protocol = ProxyServer

    def __init__(self, reactor, key):
        self.reactor = reactor
        self.key = key
        self.num_protocols = 0
        # self.crypto = crypt.MyCrypto(key)
