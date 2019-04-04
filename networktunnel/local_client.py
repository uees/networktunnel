from twisted.internet import protocol

from .logger import LogMixin


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

    def connectionLost(self, reason):
        self.set_state(self.STATE_Disconnected)
        self.log('Connection lost', self.peer_address, reason.getErrorMessage())
        self.server.client = None
        self.server.transport.loseConnection()
        self.server = None

        self.log(f"Unable to connect to peer: {reason}")

    def dataReceived(self, data):
        # data = self.server.factory.crypto.decrypt(data)
        self.server.transport.write(data)

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
