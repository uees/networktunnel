import socket
import struct

from twisted.internet import defer, protocol
from twisted.internet.endpoints import clientFromString, connectProtocol

from config import ConfigManager
from networktunnel import constants, errors
from networktunnel.base import BaseSocksServer
from networktunnel.helpers import parse_address
from networktunnel.local_client import ProxyClient, UDPProxyClient
from networktunnel.shadow import ShadowProtocol


class TransferServer(BaseSocksServer):
    """
    本地端口转发服务器, 转发 socks client 的数据, 并加密
    """

    def dataReceived(self, data):
        # 接受 socks client 的数据
        if self.is_state(self.STATE_ESTABLISHED):
            self.client.write(data)

        elif self.is_state(self.STATE_CONNECTED):  # 建立了连接
            # 这个状态下开始建立本地端口转发客户端
            self.negotiate_methods(data)

        elif self.is_state(self.STATE_SENT_METHOD):
            # 本地端口转换服务没有设计认证, 始终不会有这个状态
            self.log.error('Unexpected data, STATE: {state}', state=self._state)

        elif self.is_state(self.STATE_SENT_AUTHENTICATION_RESULT):
            # 这个状态下已经建立了端口转发客户端
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

    def on_client_auth_ok(self):
        self.log.info('client authentication success')
        self.write(struct.pack('!BB', self._version, constants.AUTH_ANONYMOUS))
        self.set_state(self.STATE_SENT_AUTHENTICATION_RESULT)
        self.transport.resumeProducing()

    def on_client_auth_error(self):
        self.log.info('client authentication failure')
        self.write(struct.pack('!BB', self._version, constants.NO_ACCEPTABLE_METHODS))
        self.set_state(self.STATE_ERROR)
        self.transport.resumeProducing()
        self.transport.loseConnection()

    def on_bind_first_reply(self):
        self.log.info('First response received with bind cmd')
        self.set_state(self.STATE_WAITING_CONNECTION)

    def on_client_established(self):
        self.log.info('local client established')
        self.set_state(self.STATE_ESTABLISHED)

    def negotiate_methods(self, data: bytes):
        """ 协商 methods """
        self.log.info('Start negotiating the certification method')
        self.set_state(self.STATE_RECEIVED_METHODS)

        if len(data) < 3:
            return defer.fail(errors.ParsingError())

        ver, nmethods = struct.unpack('!BB', data[0:2])

        d = self.check_version(ver)

        def negotiate(ignored):
            methods = struct.unpack(f'!{nmethods}B', data[2:2 + nmethods])

            if constants.AUTH_ANONYMOUS not in methods:
                raise errors.NoAcceptableMethods()

            return self.start_client().addErrback(self.on_error)

        d.addCallback(negotiate)
        d.addErrback(self.on_error)

        return d

    def parse_command(self, data: bytes):
        """ 解析命令 """
        self.log.info('Parse the request command')
        self.set_state(self.STATE_RECEIVED_COMMAND)

        if len(data) < 4:
            return defer.fail(errors.ParsingError())

        ver, cmd, rsv, atyp = struct.unpack('!4B', data[0:4])
        d = self.check_version(ver)

        def do_parse(ignored):
            """ 分配命令 """
            if cmd in (constants.CMD_CONNECT, constants.CMD_BIND):
                return data

            elif cmd == constants.CMD_UDP_ASSOCIATE:
                self.start_udp_client(atyp, data)  # 同步函数

                address = self.udp_port.getHost()

                # 修改 CMD 包, 通知 socks 服务器由本地UDP代理客户端转发数据
                request = b''.join([
                    struct.pack('!4B', self._version, constants.CMD_UDP_ASSOCIATE, constants.RSV, constants.ATYP_IPV4),
                    b''.join([socket.inet_aton(address.host), struct.pack('!H', address.port)])
                ])

                return request

            raise errors.CommandNotSupported(f"Not implement {cmd} yet!")

        def send_command(request):
            self.client.sendCommand(request)

        d.addCallback(do_parse)
        d.addCallback(send_command)
        d.addErrback(self.on_error)

        return d

    def start_udp_client(self, atyp, data):
        self.log.info('start udp client')
        # 获取 socks 客户端绑定的 UDP 端口
        org_host, org_port = parse_address(atyp, data)

        self.udp_client = UDPProxyClient(self, addr=(org_host, org_port), atyp=atyp)
        self.udp_port = self.factory.reactor.listenUDP(0, self.udp_client)

    def start_client(self):
        self.log.info('start client')

        self.transport.pauseProducing()
        conf = ConfigManager().default
        proxy_host_port = conf.get('local', 'proxy_host_port')
        point = clientFromString(self.factory.reactor, f"tcp:{proxy_host_port}")

        d = connectProtocol(point, ProxyClient(self))

        def error(failure):
            raise errors.HostUnreachable()

        d.addErrback(error)

        return d


class TransferServerFactory(protocol.Factory):
    protocol = TransferServer
    reactor = None

    def __init__(self, reactor):
        self.reactor = reactor
        self.num_protocols = 0

        conf = ConfigManager().default
        self.shadow = ShadowProtocol(
            key=conf.get('local', 'key'),
            data_salt=conf.get('local', 'data_salt'),
            pro_salt=conf.get('local', 'pro_salt'),
            data_cipher=conf.get('local', 'data_cipher'),
            pro_cipher=conf.get('local', 'pro_cipher'),
        )
