import socket
import struct

from twisted.internet import defer, protocol
from twisted.internet.address import HostnameAddress, IPv4Address, IPv6Address
from twisted.logger import Logger

from networktunnel import constants, errors
from networktunnel.helpers import socks_domain_host


class BaseSocksServer(protocol.Protocol):
    STATE_METHODS = 0x01  # 协商认证方法
    STATE_AUTH = 0x02  # 认证中
    STATE_COMMAND = 0x03  # 解析命令
    STATE_WAITING_CONNECTION = 0x04
    STATE_ESTABLISHED = 0x05  # 成功
    STATE_DISCONNECTED = 0x06
    STATE_ERROR = 0xff
    log = None

    def __init__(self):
        self.log = Logger()
        self.peer_address = None
        self.host_address = None
        self.client = None
        self.udp_port = None
        self.udp_client = None

        self._version = constants.SOCKS5_VER
        self._state = None

    def connectionMade(self):
        self.set_state(self.STATE_METHODS)
        self.peer_address = self.transport.getPeer()  # socks client address
        self.host_address = self.transport.getHost()

        self.factory.num_protocols += 1

    def connectionLost(self, reason):
        self.set_state(self.STATE_DISCONNECTED)
        if self.factory.num_protocols > 0:
            self.factory.num_protocols -= 1

        if self.client is not None and self.client.transport:
            self.client.transport.loseConnection()
            self.client = None

        if self.udp_port is not None:
            def stoped(result):
                self.udp_port = None
                self.udp_client = None

            # 不用调用 stopListening 会自动 stopListening
            # self.udp_port.stopListening().addCallbacks(stoped, self.on_error)

    def check_version(self, ver: int):
        if ver != self._version:
            self.log.warn(f'Wrong version from {self.peer_address}')
            return defer.fail(errors.InvalidServerVersion())

        return defer.succeed(ver)

    def on_error(self, failure):
        self.set_state(self.STATE_ERROR)

        self.log.failure('has an error', failure=failure)

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

    def make_reply(self, rep, address=None):
        if isinstance(address, IPv4Address):
            atyp = constants.ATYP_IPV4
            addr = socket.inet_aton(address.host)
        elif isinstance(address, IPv6Address):
            atyp = constants.ATYP_IPV6
            addr = socket.inet_pton(socket.AF_INET6, address.host)
        elif isinstance(address, HostnameAddress):
            atyp = constants.ATYP_DOMAINNAME
            addr = socks_domain_host(address.host)
        else:
            atyp = constants.ATYP_IPV4
            addr = socket.inet_aton('0.0.0.0')

        response = b''.join([
            struct.pack('!4B', self._version, rep, constants.RSV, atyp),
            b''.join([addr, struct.pack('!H', address.port)])
        ])

        self.write(response)

    def write(self, data):
        self.transport.write(data)

    def is_state(self, state):
        return self._state == state

    def set_state(self, state):
        self._state = state
