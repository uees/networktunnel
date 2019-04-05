import os
import socket
import struct

from twisted.internet import protocol
from twisted.internet.address import IPv4Address, IPv6Address

from config import get_config
from settings import BASE_DIR

from . import constants
from .helpers import parse_address, socks_domain_host
from .logger import LogMixin

cfg = get_config(os.path.join(BASE_DIR, 'local.conf'))


class ProxyClient(protocol.Protocol, LogMixin):
    """
    此客户端只需要完成协议的验证阶段
    """
    STATE_Created = 0x01
    STATE_Connected = 0x02
    STATE_SentInitialHandshake = 0x03
    STATE_ReceivedInitialHandshakeResponse = 0x04
    STATE_SentAuthentication = 0x05
    STATE_ReceivedAuthenticationResponse = 0x06
    STATE_WaitCommand = 0x07
    STATE_SentCommand = 0x08
    STATE_ReceivedCommandResponse = 0x09
    STATE_Established = 0x0a
    STATE_Disconnected = 0x0b
    STATE_Error = 0xff

    def __init__(self, server):
        self.set_state(self.STATE_Created)
        self.server = server
        self.server.client = self
        self.peer_address = None
        self.host_address = None
        self.has_udp_cmd = False

    def connectionMade(self):
        self.set_state(self.STATE_Connected)
        self.peer_address = self.transport.getPeer()
        self.host_address = self.transport.getHost()
        self.log('Connection made', self.peer_address)

        self.transport.registerProducer(self.server.transport, True)
        self.server.transport.registerProducer(self.transport, True)

        self.sendInitialHandshake()

    def connectionLost(self, reason):
        self.set_state(self.STATE_Disconnected)
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())

        if self.server is not None and self.server.transport:
            self.server.transport.loseConnection()
            self.server = None

        self.log(f"Unable to connect to peer: {reason}")

    def dataReceived(self, data):
        # 这里是接收到远程 socks 服务器的数据
        # data = self.server.factory.crypto.decrypt(data)

        if self.is_state(self.STATE_Established):
            # 转发， 命令确认后进入此状态
            self.server.transport.write(data)

        elif self.is_state(self.STATE_SentInitialHandshake):
            self.receiveInitialHandshakeResponse(data)

        elif self.is_state(self.STATE_SentAuthentication):
            self.receivedAuthenticationResponse(data)

        elif self.is_state(self.STATE_SentCommand):
            self.receiveCommandResponse(data)

    def sendInitialHandshake(self):
        self.set_state(self.STATE_SentInitialHandshake)
        request = struct.pack('!BBB', constants.SOCKS5_VER, 1, constants.AUTH_TOKEN)
        self.write(request)

    def receiveInitialHandshakeResponse(self, data):
        self.set_state(self.STATE_ReceivedInitialHandshakeResponse)
        ver, method = struct.unpack('!BB', data)
        if method != constants.AUTH_TOKEN:
            self.log('Unsupported methods!')
            self.transport.loseConnection()
        else:
            self.sendAuthentication()

    def sendAuthentication(self):
        self.set_state(self.STATE_SentAuthentication)
        token = cfg.get('default', 'token', fallback='').encode()
        request = b''.join([struct.pack('!BB', constants.SOCKS5_VER, len(token)), token])
        self.write(request)

    def receivedAuthenticationResponse(self, data):
        self.set_state(self.STATE_ReceivedAuthenticationResponse)
        ver, status = struct.unpack('!BB', data)

        if status == 1:
            # 等待 self.server 封装命令
            self.set_state(self.STATE_WaitCommand)
            self.server.on_client_auth_ok()
        else:
            self.set_state(self.STATE_Error)
            self.transport.loseConnection()

    def sendCommand(self, data, is_udp=False):
        self.set_state(self.STATE_SentCommand)
        self.has_udp_cmd = is_udp
        self.write(data)

    # +----+-----+-------+------+----------+----------+
    # | VER | REP | RSV | ATYP | BND.ADDR | BND.PORT |
    # +----+-----+-------+------+----------+----------+
    # |  1 |  1  | X'00' |  1   | Variable | 2       |
    # +----+-----+-------+------+----------+----------+
    def receiveCommandResponse(self, data):
        self.set_state(self.STATE_ReceivedCommandResponse)

        ver, rep = struct.unpack('!BB', data[:2])
        if rep == constants.SOCKS5_GRANTED:
            if self.has_udp_cmd:
                self.has_udp_cmd = False
                # 获取并保存地址信息
                atyp = ord(data[3:4])
                host, port = parse_address(atyp, data)
                self.server.upd_client.set_peer((host, port), atyp)

                # 修改地址信息, 通知 socks 客户端由本地另一UPD端口转发数据
                address = self.server.upd_client.address
                if isinstance(address, IPv4Address):
                    addr = socket.inet_aton(address.host)
                    addr_type = constants.ATYP_IPV4
                elif isinstance(address, IPv6Address):
                    addr = socket.inet_pton(socket.AF_INET6, address.host)
                    addr_type = constants.ATYP_IPV6
                else:
                    addr = socks_domain_host(address.host)
                    addr_type = constants.ATYP_DOMAINNAME

                data = b''.join([
                    struct.pack('!4B', ver, rep, constants.RSV, addr_type),
                    b''.join([addr, struct.pack('!H', address.port)])
                ])

            self.set_state(self.STATE_Established)
            self.server.on_client_established()
            self.server.transport.write(data)
        else:
            self.set_state(self.STATE_Error)
            self.server.transport.write(data)
            self.transport.loseConnection()

    def write(self, data):
        # data = self.server.factory.crypto.encrypt(data)
        self.transport.write(data)

    def is_state(self, state):
        return self._state == state

    def set_state(self, state):
        self._state = state


class UDPProxyClient(protocol.DatagramProtocol):
    """与远端 UDP PROXY 交换数据 加密解密"""

    def __init__(self, server, addr, atyp):
        self.server = server
        self.address = None

        self.origin_addr = addr  # socks client
        self.origin_atyp = atyp

        self.peer_addr = None  # socks server
        self.peer_atyp = None

    def startProtocol(self):
        self.address = self.transport.getHost()

    def datagramReceived(self, data, addr):
        if addr == self.origin_addr:
            # todo 加密
            self.transport.write(data, self.peer_addr)
        elif addr == self.peer_addr:
            # todo 解密
            self.transport.write(data, self.origin_addr)

    def connectionRefused(self):
        # 如果没有服务器监听我们发送到的地址，则调用。
        self.log('some udp data lose')

    def set_peer(self, addr, atyp):
        self.peer_addr = addr
        self.peer_atyp = atyp
