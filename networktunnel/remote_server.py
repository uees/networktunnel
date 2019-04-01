# -*- coding: utf-8 -*-
import socket
import struct

from twisted.internet import protocol, reactor, defer, threads
from twisted.internet.address import IPv4Address, IPv6Address, HostnameAddress
from twisted.protocols import policies
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol

from config import ConfigFactory

from . import errors, constants
from .helpers import get_method, socks_domain_host
from .logger import LogMixin


class RemoteSocksV5Server(policies.TimeoutMixin, LogMixin, protocol.Protocol):
    STATE_IGNORED = 0x00
    STATE_METHODS = 0x01  # 协商认证方法
    STATE_AUTH = 0x02  # 认证中
    STATE_COMMAND = 0x03  # 解析命令
    STATE_PIPELINE = 0x05  # 建立管道传输

    PIPE_TCP = 0x01
    PIPE_UDP = 0x03

    def __init__(self):
        self.client = None
        self.buff = b''

        self._version = constants.SOCKS5_VER
        self._state = self.STATE_METHODS
        self._auth_types = [constants.AUTH_TOKEN]
        self._auth_method = None
        self._pipe_type = None

    def connectionMade(self):
        self.log('Connection made', self.transport.getPeer())
        self.setTimeout(self.factory.timeout)

    def timeoutConnection(self):
        self.log('Connection time', self.transport.getPeer())
        super().timeoutConnection()

    def connectionLost(self, reason):
        self.log('Connection lost', self.transport.getPeer(), reason.getErrorMessage())

        # Remove client
        if self.client is not None and self.client.transport:
            self.client.transport.loseConnection()
        self.client = None

    def dataReceived(self, data):
        # todo 解密
        # data = self.factory.crypto.decrypt(data)

        if self.is_state(self.STATE_PIPELINE):
            return self.client.write(data)

        if self.is_state(self.STATE_IGNORED):
            return

        self.resetTimeout()

        if self.is_state(self.STATE_METHODS):
            return self.negotiate_methods(data).addErrback(self.on_error)

        if self.is_state(self.STATE_AUTH):
            if self._auth_method == constants.AUTH_TOKEN:
                return self.auth_token(data).addErrback(self.on_error)

            return defer.fail(errors.LoginAuthenticationFailed()).addErrback(self.on_error)

        if self.is_state(self.STATE_COMMAND):
            return self.parse_cmd(data)

    def write(self, data):
        # todo 加密
        # data = self.factory.crypto.encrypt(data)
        self.transport.write(data)

    def on_error(self, failure):
        self.set_state(self.STATE_IGNORED)

        server_address = self.transport.getHost()

        if isinstance(failure, errors.NoAcceptableMethods):
            self.write(struct.pack('!BB', self._version, constants.NO_ACCEPTABLE_METHODS))
        elif isinstance(failure, errors.LoginAuthenticationFailed):
            self.write(struct.pack('!BB', self._version, constants.AUTH_ERROR))
        elif isinstance(failure, errors.CommandNotSupported):
            self.make_reply(constants.SOCKS5_COMMAND_NOT_SUPPORTED, server_address)
        elif isinstance(failure, errors.HostUnreachable):
            self.make_reply(constants.SOCKS5_HOST_UNREACHABLE, server_address)
        elif isinstance(failure, errors.AddressNotSupported):
            self.make_reply(constants.SOCKS5_ADDRESS_TYPE_NOT_SUPPORTED, server_address)
        else:
            self.make_reply(constants.SOCKS5_GENERAL_FAILURE, server_address)

        self.transport.loseConnection()

    def check_version(self, ver: int):
        if ver != self._version:
            self.log('Wrong version from %s' % str(self.transport.getPeer()))
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
        self.check_version(ver).addErrback(self.on_error)

        methods = struct.unpack('!%dB' % nmethods, data[2:2 + nmethods])
        self._auth_method = get_method(methods, self._auth_types)

        if self._auth_method == constants.NO_ACCEPTABLE_METHODS:
            return defer.fail(errors.NoAcceptableMethods())

        if self._auth_method == constants.AUTH_ANONYMOUS:
            self.set_state(self.STATE_COMMAND)
        else:
            self.set_state(self.STATE_AUTH)

        self.write(struct.pack('!BB', self._version, self._auth_method))

        return defer.succeed(True)

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
        self.check_version(ver).addErrback(self.on_error)

        token = data[2:2 + token_length].decode()

        d = auth_token(token)

        def on_success(result):
            self.set_state(self.STATE_COMMAND)
            self.transport.write(struct.pack('!BB', self._version, constants.AUTH_SUCCESS))

        d.addCallback(on_success)

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
    def parse_cmd(self, data: bytes):
        if len(data) < 4:
            return defer.fail(errors.ParsingError())

        ver, cmd, rsv, atyp = struct.unpack('!4B', data[0:4])
        self.check_version(ver).addErrback(self.on_error)

        if cmd == constants.CMD_CONNECT:
            def success(address):
                domain, port = address
                d = self.cmd_connect(domain, port)
                d.addErrback(self.on_error)

            return self.parse_connect(atyp, data).addCallbacks(success, self.on_error)

        if cmd == constants.CMD_BIND:
            return self.cmd_bind()

        if cmd == constants.CMD_UDP_ASSOCIATE:
            return self.cmd_udp()

        return defer.fail(errors.CommandNotSupported(f"Not implement {cmd} yet!"))

    def parse_connect(self, atype: int, data: bytes):
        cur = 4
        if atype == constants.ATYP_DOMAINNAME:
            domain_len = ord(data[cur:cur + 1])
            cur += 1

            domain = data[cur:cur + domain_len].decode()
            cur += domain_len

        elif atype == self.ATYP_IPV4:
            domain = socket.inet_ntop(socket.AF_INET, data[cur:cur + 4])
            cur += 4

        elif atype == self.ATYP_IPV6:
            domain = socket.inet_ntop(socket.AF_INET6, data[cur:cur + 16])
            cur += 16

        else:
            return defer.fail(errors.AddressNotSupported("Unknown address type!"))

        port = struct.unpack('!H', data[cur:cur + 2])[0]

        return defer.succeed((domain, port))

    def cmd_connect(self, domain: str, port: int):
        from .remote_client import RemoteTCPClient

        point = TCP4ClientEndpoint(reactor, domain, port)
        d = connectProtocol(point, RemoteTCPClient(self))

        def success(result):
            self.setTimeout(None)  # 取消超时
            self.set_state(self.STATE_PIPELINE)
            self.log("connect to {}, {}".format(domain, port))

        d.addCallback(success)

        def error(failure):
            raise errors.HostUnreachable()

        d.addErrback(error)

        return d

    def cmd_bind(self):
        pass

    def cmd_udp(self):
        pass

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
            response = struct.pack('!4B', self._version, rep)
            self.write(response)
            raise errors.AddressNotSupported()

        self.write(response)


class RemoteSocksV5ServerFactory(protocol.Factory):
    protocol = RemoteSocksV5Server

    def __init__(self):
        self.config = ConfigFactory.get_config()
        self.timeout = self.config.getTimeOut()
