# -*- coding: utf-8 -*-
import socket
import struct

from twisted.internet import protocol, defer
from twisted.internet.address import IPv4Address, IPv6Address, HostnameAddress
from twisted.protocols import policies
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

from config import ConfigFactory

from .remote_client import RemoteTCPClient, RemoteTCPClientFactory
from . import errors, constants
from .helpers import get_method, socks_domain_host, parse_address
from .logger import LogMixin


class State:
    IGNORED = 0x00
    METHODS = 0x01  # 协商认证方法
    AUTH = 0x02  # 认证中
    COMMAND = 0x03  # 解析命令
    WAITING_CONNECTION = 0x04
    TCP_PIPELINE = 0x05  # 建立 connect TCP 管道传输
    BIND_PIPELINE = 0x06  # bind 成功
    UDP_PIPELINE = 0x07


class RemoteSocksV5Server(policies.TimeoutMixin, LogMixin, protocol.Protocol):

    def __init__(self):
        self.client = None
        self.peer_address = None
        self.host_address = None

        self._version = constants.SOCKS5_VER
        self._state = State.METHODS
        self._auth_types = [constants.AUTH_ANONYMOUS, constants.AUTH_TOKEN]
        self._auth_method = None
        self._pipe_type = None

    def connectionMade(self):
        self.peer_address = self.transport.getPeer()
        self.host_address = self.transport.getHost()
        self.log('Connection made', self.peer_address)
        # self.setTimeout(self.factory.config.getTimeOut())

    def timeoutConnection(self):
        self.log('Connection time', self.peer_address)
        super().timeoutConnection()

    def connectionLost(self, reason):
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())

        # self.setTimeout(None)

        # Remove client
        if self.client is not None and self.client.transport:
            self.client.transport.loseConnection()
        self.client = None

    def dataReceived(self, data):
        # todo 解密
        # data = self.factory.crypto.decrypt(data)

        def reset_timeout(ignored):
            self.resetTimeout()

        if self.is_state(State.TCP_PIPELINE):
            self.client.write(data)

        elif self.is_state(State.METHODS):
            d = self.negotiate_methods(data)
            d.addCallbacks(reset_timeout, self.on_error)

        elif self.is_state(State.AUTH):
            if self._auth_method == constants.AUTH_TOKEN:
                d = self.auth_token(data)
                d.addCallbacks(reset_timeout, self.on_error)

            else:
                self.on_error(errors.LoginAuthenticationFailed())

        elif self.is_state(State.COMMAND):
            d = self.parse_command(data)
            d.addErrback(self.on_error)

    def write(self, data):
        # todo 加密
        # data = self.factory.crypto.encrypt(data)
        self.transport.write(data)

    def on_error(self, failure):
        self.set_state(State.IGNORED)

        server_address = self.transport.getHost()

        # failure.value is the exception instance responsible for this failure.
        if isinstance(failure, Exception):
            error = failure
        else:
            error = failure.value

        if isinstance(error, (errors.NoAcceptableMethods, errors.LoginAuthenticationFailed)):
            self.write(struct.pack('!BB', self._version, error.code))
        else:
            if hasattr(error, 'code'):
                self.make_reply(error.code, server_address)
            else:
                self.write(b'\x00')

        self.transport.loseConnection()

    def check_version(self, ver: int):
        if ver != self._version:
            self.log(f'Wrong version from {self.peer_address}')
            return defer.fail(errors.InvalidServerVersion())

        return defer.succeed(True)

    # request
    # +----+----------+----------+
    # | VER | NMETHODS | METHODS |
    # +----+----------+----------+
    # |  1  |    1    | 1 to 255 |
    # +----+----------+----------+
    #
    # response
    # +----+---------+
    # | VER | METHOD |
    # +-----+--------+
    # |  1  |  1     |
    # +-----+--------+
    def negotiate_methods(self, data: bytes):
        """ 协商 methods """
        if len(data) < 3:
            return defer.fail(errors.ParsingError())

        ver, nmethods = struct.unpack('!BB', data[0:2])

        d = self.check_version(ver)

        def negotiate(ignored):
            methods = struct.unpack('!%dB' % nmethods, data[2:2 + nmethods])
            self._auth_method = get_method(methods, self._auth_types)

            if self._auth_method == constants.NO_ACCEPTABLE_METHODS:
                raise errors.NoAcceptableMethods()

            if self._auth_method == constants.AUTH_ANONYMOUS:
                self.set_state(State.COMMAND)
            else:
                self.set_state(State.AUTH)

            self.write(struct.pack('!BB', self._version, self._auth_method))

        d.addCallback(negotiate)

        return d

    # request
    # +----+------+----------+
    # | VER | ULEN | UTOKEN  |
    # +----+------+----------+
    # |  1 |  1   | 1 to 255 |
    # +----+------+----------+
    #
    # response
    # +----+---------+
    # | VER | STATUS |
    # +-----+--------+
    # |  1  |  1     |
    # +-----+--------+
    def auth_token(self, data: bytes):
        from .auth import auth_token

        if len(data) < 3:
            return defer.fail(errors.ParsingError())

        ver, token_length = struct.unpack('!2B', data[0:2])
        d = self.check_version(ver)

        def do_auth(ignored):

            token = data[2:2 + token_length].decode()

            dd = auth_token(token)

            def on_success(result):
                self.set_state(State.COMMAND)
                self.transport.write(struct.pack('!BB', self._version, constants.AUTH_SUCCESS))

            dd.addCallback(on_success)

            return dd

        d.addCallback(do_auth)

        return d

    #    +----+-----+-------+------+----------+----------+
    #    |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
    #    +----+-----+-------+------+----------+----------+
    #    | 1  |  1  | X'00' |  1   | Variable |    2     |
    #    +----+-----+-------+------+----------+----------+
    #
    # +----+-----+-------+------+----------+----------+
    # | VER | REP | RSV | ATYP | BND.ADDR | BND.PORT |
    # +----+-----+-------+------+----------+----------+
    # |  1 |  1  | X'00' |  1   | Variable | 2       |
    # +----+-----+-------+------+----------+----------+
    def parse_command(self, data: bytes):
        """ 解析命令 """
        if len(data) < 4:
            return defer.fail(errors.ParsingError())

        ver, cmd, rsv, atyp = struct.unpack('!4B', data[0:4])
        d = self.check_version(ver)

        def assign_command(ignored):
            """ 分配命令 """
            if cmd == constants.CMD_CONNECT:
                domain, port = parse_address(atyp, data)  # maybe raise AddressNotSupported
                return self.do_connect(domain, port)  # defer

            if cmd == constants.CMD_BIND:
                return self.do_bind()  # defer

            if cmd == constants.CMD_UDP_ASSOCIATE:
                return self.do_udp_associate()  # defer

            raise errors.CommandNotSupported(f"Not implement {cmd} yet!")

        d.addCallback(assign_command)

        return d

    def do_connect(self, domain: str, port: int):
        """
        If using CONNECT, the client is now in the established state.
        :param domain:
        :param port:
        :return:
        """
        # Don't read anything from the connecting client until we have somewhere to send it to.
        self.transport.pauseProducing()

        point = TCP4ClientEndpoint(self.factory.reactor, domain, port)
        d = connectProtocol(point, RemoteTCPClient(self))

        def success(result):
            self.log("connect to {}, {}".format(domain, port))
            self.set_state(State.TCP_PIPELINE)
            # self.setTimeout(None)  # 取消超时

            # We're connected, everybody can read to their hearts content.
            self.transport.resumeProducing()

            self.make_reply(constants.SOCKS5_GRANTED, address=self.client.host_address)

        d.addCallback(success)

        def error(failure):
            raise errors.HostUnreachable()

        d.addErrback(error)

        return d

    def do_bind(self):
        """
        If using BIND, the Socks client is now in BoundWaitingForConnection state.
        This means that the remote proxy server is waiting for a remote connection to the bound port.
        :return: defer
        """
        return defer.fail(errors.CommandNotSupported())

    def do_udp_associate(self):
        """
        If using Associate, the Socks client is now Established. And the proxy server is now accepting UDP packets at the
        given bound port. This initial Socks TCP connection must remain open for the UDP relay to continue to work.
        :return:
        """
        return defer.fail(errors.CommandNotSupported())

    def send_data(self, data):
        pass

    def is_state(self, state):
        return self._state == state

    def set_state(self, state):
        self._state = state

    def make_reply(self, rep, address=None):
        if isinstance(address, IPv4Address):
            response = b''.join([
                struct.pack('!4B', self._version, rep, constants.RSV, constants.ATYP_IPV4),
                b''.join([socket.inet_aton(address.host), struct.pack('!H', address.port)])
            ])
        elif isinstance(address, IPv6Address):
            response = b''.join([
                struct.pack('!4B', self._version, rep, constants.RSV, constants.ATYP_IPV6),
                b''.join([socket.inet_aton(address.host), struct.pack('!H', address.port)])
            ])
        elif isinstance(address, HostnameAddress):
            response = b''.join([
                struct.pack('!4B', self._version, rep, constants.RSV, constants.ATYP_DOMAINNAME),
                b''.join([socks_domain_host(address.host), struct.pack('!H', address.port)])
            ])
        else:
            response = b''.join([
                struct.pack('!4B', self._version, rep, constants.RSV, constants.ATYP_IPV4),
                b''.join([socket.inet_aton('0.0.0.0'), struct.pack('!H', address.port)])
            ])

        self.write(response)


class RemoteSocksV5ServerFactory(protocol.Factory):
    protocol = RemoteSocksV5Server

    def __init__(self, reactor):
        self.reactor = reactor
        self.config = ConfigFactory.get_config()