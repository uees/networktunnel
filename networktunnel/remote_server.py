# -*- coding: utf-8 -*-
import socket
import struct

from twisted.internet import defer, protocol
from twisted.internet.endpoints import (clientFromString, connectProtocol,
                                        serverFromString)

from config import ConfigManager
from networktunnel import constants, errors
from networktunnel.base import BaseSocksServer
from networktunnel.helpers import get_method, parse_address
from networktunnel.remote_client import (BindProxyClientFactory, ProxyClient,
                                         UdpProxyClient)
from networktunnel.shadow import ShadowProtocol


class SocksServer(BaseSocksServer):

    def __init__(self):
        super().__init__()

        self._auth_types = [constants.AUTH_TOKEN]
        self._auth_method = None

    def connectionMade(self):
        super().connectionMade()

        # next 2 line do 直接从认证开始
        self.set_state(self.STATE_SENT_METHOD)
        self._auth_method = constants.AUTH_TOKEN

        self.log.info('Connection made {address}', address=self.peer_address)

    def connectionLost(self, reason):
        self.log.info('Connection lost {address} {message}',
                      address=self.peer_address,
                      message=reason.getErrorMessage())
        super().connectionLost(reason)

    def dataReceived(self, data):
        # 解密
        if self.is_state(self.STATE_ESTABLISHED):
            data = self.factory.shadow.decrypt_data(data)
        else:
            data = self.factory.shadow.decrypt_protocol_data(data)

        if self.is_state(self.STATE_ESTABLISHED):  # 所有就绪
            self.client.write(data)

        elif self.is_state(self.STATE_CONNECTED):  # 建立了连接
            self.negotiate_methods(data)

        elif self.is_state(self.STATE_SENT_METHOD):  # 发送了认证方法
            if self._auth_method == constants.AUTH_TOKEN:
                self.auth_token(data)
            else:
                self.on_error(errors.LoginAuthenticationFailed())

        elif self.is_state(self.STATE_SENT_AUTHENTICATION_RESULT):  # 解析命令
            self.parse_command(data)

        elif self.is_state(self.STATE_ERROR):
            self.transport.loseConnection()

        else:
            # 这些状态下应该是不会有数据发送过来的
            # STATE_RECEIVED_METHODS
            # STATE_RECEIVED_AUTHENTICATION
            # STATE_RECEIVED_COMMAND
            # STATE_WAITING_CONNECTION
            # STATE_DISCONNECTED
            # STATE_ERROR
            self.log.error('Unexpected data, STATE: {state}', state=self._state)

    def write(self, data):
        # 加密
        if self.is_state(self.STATE_ESTABLISHED):
            data = self.factory.shadow.encrypt_data(data)
        else:
            data = self.factory.shadow.encrypt_protocol_data(data)
        self.transport.write(data)

    def on_bind_connect_success(self):
        # 第二个回复在预期的传入连接成功或失败之后发生
        self.log.info('Second response received with bind cmd')
        self.make_reply(constants.SOCKS5_GRANTED, address=self.client.peer_address)
        self.set_state(self.STATE_ESTABLISHED)

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
        self.log.info('Start negotiating the certification method')
        self.set_state(self.STATE_RECEIVED_METHODS)
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
                next_state = self.STATE_SENT_AUTHENTICATION_RESULT
            else:
                next_state = self.STATE_SENT_METHOD

            self.write(struct.pack('!BB', self._version, self._auth_method))
            self.set_state(next_state)

        d.addCallback(negotiate)
        d.addErrback(self.on_error)

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

        self.log.info('Start auth token')
        self.set_state(self.STATE_RECEIVED_AUTHENTICATION)
        if len(data) < 3:
            return defer.fail(errors.ParsingError())

        ver, token_length = struct.unpack('!2B', data[0:2])
        d = self.check_version(ver)

        def do_auth(ignored):
            token = data[2:2 + token_length].decode()

            dd = auth_token(token)

            def on_success(result):
                self.write(struct.pack('!BB', self._version, constants.AUTH_SUCCESS))
                self.set_state(self.STATE_SENT_AUTHENTICATION_RESULT)

            dd.addCallback(on_success)

            return dd

        d.addCallback(do_auth)
        d.addErrback(self.on_error)

        return d

    # +----+-----+-------+------+----------+----------+
    # |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
    # +----+-----+-------+------+----------+----------+
    # | 1  |  1  | X'00' |  1   | Variable |    2     |
    # +----+-----+-------+------+----------+----------+
    #
    # +----+-----+-------+------+----------+----------+
    # | VER | REP | RSV | ATYP | BND.ADDR | BND.PORT |
    # +----+-----+-------+------+----------+----------+
    # |  1 |  1  | X'00' |  1   | Variable | 2       |
    # +----+-----+-------+------+----------+----------+
    def parse_command(self, data: bytes):
        """ 解析命令 """
        self.log.info('Parse the request command')
        self.set_state(self.STATE_RECEIVED_COMMAND)

        if len(data) < 4:
            return defer.fail(errors.ParsingError())

        ver, cmd, rsv, atyp = struct.unpack('!4B', data[0:4])
        d = self.check_version(ver)

        def assign_command(ignored):
            """ 分配命令 """
            self.log.info('assign command')

            domain, port = parse_address(atyp, data)  # maybe raise AddressNotSupported
            if cmd == constants.CMD_CONNECT:
                return self.do_connect(domain, port).addErrback(self.on_error)  # defer

            if cmd == constants.CMD_BIND:
                return self.do_bind(domain, port).addErrback(self.on_error)  # defer

            if cmd == constants.CMD_UDP_ASSOCIATE:
                return self.do_udp_associate(domain, port, atyp)  # defer

            raise errors.CommandNotSupported(f"Not implement {cmd} yet!")

        d.addCallback(assign_command)
        d.addErrback(self.on_error)

        return d

    def do_connect(self, domain: str, port: int):
        """
        If using CONNECT, the client is now in the established state.
        :param domain: 服务端地址
        :param port: 服务端端口
        :return: defer
        """
        self.log.info('do connect command')
        # Don't read anything from the connecting client until we have somewhere to send it to.
        self.transport.pauseProducing()

        point = clientFromString(self.factory.reactor, f"tcp:host={domain}:port={port}")
        d = connectProtocol(point, ProxyClient(self))

        def success(ignored):
            self.log.info("connected to {domain}, {port}", domain=domain, port=port)

            # We're connected, everybody can read to their hearts content.
            self.transport.resumeProducing()

            self.make_reply(constants.SOCKS5_GRANTED, address=self.client.host_address)
            self.set_state(self.STATE_ESTABLISHED)

        def error(failure):
            raise errors.HostUnreachable()

        d.addCallbacks(success, error)

        return d

    def do_bind(self, host: str, port: int):
        """
        If using BIND, the Socks client is now in BoundWaitingForConnection state.
        This means that the remote proxy server is waiting for a remote connection to the bound port.
        :param host: 建议 SOCKS 服务器使用监听地址
        :param port: 建议 SOCKS 服务器使用监听端口
        :return: defer
        """
        self.log.info('do bind command')

        self.transport.pauseProducing()

        def first_reply(listening_port):
            self.log.info('first reply')
            # 第一次回复是在服务器创建并绑定一个新的套接字之后发送的
            self.make_reply(constants.SOCKS5_GRANTED, listening_port.getHost())
            self.set_state(self.STATE_WAITING_CONNECTION)

        endpoint = serverFromString(self.factory.reactor, f"tcp:{port}:interface={host}")
        # https://twistedmatrix.com/documents/current/api/twisted.internet.interfaces.IStreamServerEndpoint.html#listen
        d = endpoint.listen(BindProxyClientFactory(self))
        d.addCallback(first_reply)

        return d

    def do_udp_associate(self, host: str, port: int, atyp: int):
        """
        If using Associate, the Socks client is now Established. And the proxy server is now accepting UDP packets at the
        given bound port. This initial Socks TCP connection must remain open for the UDP relay to continue to work.
        :param host: 客户端希望用于发生 UDP 数据报的 ip 地址
        :param port: 客户端希望用于发生 UDP 数据报的端口
        :param atyp: 地址类型
        :return: defer
        """
        self.log.info('do udp associate command')

        # fix :: 0.0.0.0
        if host == socket.inet_aton('0.0.0.0') or host == socket.inet_pton(socket.AF_INET6, '::'):
            host = self.peer_address.host

        self.udp_client = UdpProxyClient(self, addr=(host, port), atyp=atyp)
        self.udp_port = self.factory.reactor.listenUDP(0, self.udp_client)
        self.make_reply(constants.SOCKS5_GRANTED, self.udp_port.getHost())
        self.set_state(self.STATE_ESTABLISHED)
        self.log.info('udp command success')

        return defer.succeed(self.udp_port)


class SocksServerFactory(protocol.Factory):
    protocol = SocksServer

    def __init__(self, reactor):
        self.num_protocols = 0
        self.reactor = reactor

        conf = ConfigManager().default
        self.shadow = ShadowProtocol(
            key=conf.get('remote', 'key'),
            data_salt=conf.get('remote', 'data_salt'),
            pro_salt=conf.get('remote', 'pro_salt'),
            data_cipher=conf.get('remote', 'data_cipher'),
            pro_cipher=conf.get('remote', 'pro_cipher'),
        )
