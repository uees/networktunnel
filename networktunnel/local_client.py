import os
import struct

from twisted.internet import protocol

from config import get_config
from settings import BASE_DIR

from . import constants
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
    STATE_Established = 0x07
    STATE_Disconnected = 0x08
    STATE_Error = 0xff

    def __init__(self, server):
        self.set_state(self.STATE_Created)
        self.server = server
        self.server.client = self
        self.peer_address = None
        self.host_address = None

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
        self.server.client = None
        self.server.transport.loseConnection()
        self.server = None

        self.log(f"Unable to connect to peer: {reason}")

    def dataReceived(self, data):
        # data = self.server.factory.crypto.decrypt(data)

        if self.is_state(self.STATE_Established):
            self.server.transport.write(data)

        elif self.is_state(self.STATE_SentInitialHandshake):
            self.receiveInitialHandshakeResponse(data)

        elif self.is_state(self.STATE_SentAuthentication):
            self.receivedAuthenticationResponse(data)

    def sendInitialHandshake(self):
        request = struct.pack('!BBB', constants.SOCKS5_VER, 1, constants.AUTH_TOKEN)
        self.write(request)
        self.set_state(self.STATE_SentInitialHandshake)

    def receiveInitialHandshakeResponse(self, data):
        self.set_state(self.STATE_ReceivedInitialHandshakeResponse)
        ver, method = struct.unpack('!BB', data)
        if method != constants.AUTH_TOKEN:
            self.log('Unsupported methods!')
            self.transport.loseConnection()
        else:
            token = cfg.get('default', 'token', fallback='').encode()
            request = struct.pack('!BB', constants.SOCKS5_VER, len(token)) + token
            self.write(request)
            self.set_state(self.STATE_SentAuthentication)

    def receivedAuthenticationResponse(self, data):
        self.set_state(self.STATE_ReceivedAuthenticationResponse)
        ver, status = struct.unpack('!BB', data)

        if status == 1:
            self.set_state(self.STATE_Established)
            self.server.reply_auth_ok()
        else:
            self.set_state(self.STATE_Error)
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
    pass
