# -*- coding: utf-8 -*-

from twisted.internet import protocol
from twisted.protocols import policies
from twisted.python import log

from config import ConfigFactory

AUTH_ANONYMOUS, AUTH_LOGIN = 0x00, 0x80  # 0x80 自定义 Login
ATYP_IPV4, ATYP_DOMAINNAME, ATYP_IPV6 = 0x01, 0x03, 0x04
CMD_CONNECT, CMD_BIND, CMD_UDP_ASSOCIATE = 0x01, 0x02, 0x03
NO_ACCEPTABLE_METHODS = 0xff
RSV = 0x00  # 保留字

SOCKS5_VER = 0x05
SOCKS5_GRANTED = SOCKS5_SUCCEEDED = 0x00
SOCKS5_GENERAL_FAILURE = SOCKS5_SERVER_FAILURE = 0x01
SOCKS5_REJECTED = SOCKS5_CONNECTION_NOT_ALLOWED_BY_RULESET = 0x02
SOCKS5_NETWORK_UNREACHABLE = 0x03
SOCKS5_HOST_UNREACHABLE = 0x04
SOCKS5_CONNECTION_REFUSED = 0x05
SOCKS5_TTL_EXPIRED = 0x06
SOCKS5_COMMAND_NOT_SUPPORTED = 0x07
SOCKS5_ADDRESS_TYPE_NOT_SUPPORTED = 0x08

config = ConfigFactory()


class SocksV5Protocol(policies.TimeoutMixin, protocol.Protocol):
    STATE_IGNORED = 0x00
    STATE_METHODS = 0x01
    STATE_AUTHREQ = 0x02
    STATE_REQUEST = 0x03
    STATE_REQUEST_UDP = 0x04
    STATE_RECEIVE = 0x05


class OProxyProtocol(protocol.Protocol):

    def __init__(self, father):
        self._father = father

    def connectionMade(self):

        # Get peer
        peer = self.transport.getPeer()

        if config.getLogLevel() >= 3:
            log.msg('Connection made', peer)

        if self._father._buffered:
            self.write(self._father._buffered)
            # Clean buffer
            self._father._buffered = b''

        self._father.makeReply(0x00, port=peer.port, server=peer.host)
        self._father.setOutgoing(self)

        # Ok, set normal state
        self._father.setState(self._father.STATE_RECEIVE)

        # For FAST transfer
        self._father.dataReceived, self.dataReceived = self.write, self._father.write

        if config.getLogLevel() >= 3:
            # Ok session
            log.msg('Connect ok to "%s:%d" request from %s' % (
                self.transport.getPeer().host, self.transport.getPeer().port, str(self._father.transport.getPeer())
            ))

    def connectionLost(self, reason):

        if config.getLogLevel() >= 3:
            log.msg('Connection lost', self.transport.getPeer(), reason.getErrorMessage())

        self._father.setOutgoing(None)

        # Close connection
        self._father.transport.loseConnection()

    def dataReceived(self, data):
        self._father.write(data)

    def write(self, data):
        '''
        if config.getLogLevel() >= 4:
            log.msg('%s send %r' % (
                self, data
            ))
        '''
        self.transport.write(data)
