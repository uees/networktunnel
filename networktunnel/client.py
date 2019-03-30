# -*- coding: utf-8 -*-

import struct

from zope.interface import implementer, directlyProvides, providedBy
from twisted.internet import defer, interfaces
from twisted.internet.protocol import Protocol
from twisted.protocols import tls, policies
from twisted.python.failure import Failure


class SOCKSError(Exception):
    def __init__(self, value):
        Exception.__init__(self)
        self.code = value


class SOCKSv5ClientProtocol(policies.ProtocolWrapper):
    def __init__(self, factory, wrappedProtocol, connectedDeferred, host, port, optimistic=False):
        super().__init__(factory, wrappedProtocol)
        self._connectedDeferred = connectedDeferred
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._buf = b''
        self.state = 0

    def error(self, error):
        if not self._optimistic:
            self._connectedDeferred.errback(error)
        else:
            errorcode = 600 + error.value.code
            self.wrappedProtocol.dataReceived(b"HTTP/1.1 %r ANTANI\r\n\r\n" % errorcode)

        self.transport.abortConnection()
        self.transport = None

    def socks_state_0(self):
        # error state
        self.error(SOCKSError(0x00))
        return

    def socks_state_1(self):
        if len(self._buf) < 2:
            return

        if self._buf[:2] != "\x05\x00":
            # Anonymous access denied
            self.error(Failure(SOCKSError(0x00)))
            return

        self._buf = self._buf[2:]

        if not self._optimistic:
            self.transport.write(
                struct.pack("!BBBBB", 5, 1, 0, 3, len(self._host)) + self._host + struct.pack("!H", self._port))

        self.state = 2
        getattr(self, 'socks_state_%s' % self.state)()

    def socks_state_2(self):
        if len(self._buf) < 2:
            return

        if self._buf[:2] != "\x05\x00":
            self.error(Failure(SOCKSError(ord(self._buf[1]))))
            return

        self._buf = self._buf[2:]

        self.state = 3
        getattr(self, 'socks_state_%s' % self.state)()

    def socks_state_3(self):
        if len(self._buf) < 8:
            return

        self._buf = self._buf[8:]

        if not self._optimistic:
            self.wrappedProtocol.makeConnection(self)
            try:
                self._connectedDeferred.callback(self.wrappedProtocol)
            except Exception:
                pass

        if len(self._buf):
            self.wrappedProtocol.dataReceived(self._buf)

        self._buf = ''

        self.state = 4

    def makeConnection(self, transport):
        """
        When a connection is made, register this wrapper with its factory,
        save the real transport, and connect the wrapped protocol to this
        L{ProtocolWrapper} to intercept any transport calls it makes.
        """
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.factory.registerProtocol(self)

        # We implement only Anonymous access
        self.transport.write(struct.pack("!BB", 5, len("\x00")) + b"\x00")

        if self._optimistic:
            self.transport.write(
                struct.pack("!BBBBB", 5, 1, 0, 3, len(self._host)) + self._host + struct.pack("!H", self._port))
            self.wrappedProtocol.makeConnection(self)
            try:
                self._connectedDeferred.callback(self.wrappedProtocol)
            except Exception:
                pass

        self.state = 1

    def dataReceived(self, data):
        if self.state != 4:
            self._buf = ''.join([self._buf, data])
            getattr(self, 'socks_state_%s' % self.state)()
        else:
            self.wrappedProtocol.dataReceived(data)


class SOCKSv5ClientFactory(policies.WrappingFactory):
    protocol = SOCKSv5ClientProtocol

    def __init__(self, wrappedFactory, host, port, optimistic):
        super().__init__(wrappedFactory)
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._onConnection = defer.Deferred()

    def buildProtocol(self, addr):
        try:
            proto = self.wrappedFactory.buildProtocol(addr)
        except Exception:
            self._onConnection.errback()
        else:
            return self.protocol(self, proto, self._onConnection,
                                 self._host, self._port, self._optimistic)

    def clientConnectionFailed(self, connector, reason):
        self._onConnection.errback(reason)

    def clientConnectionLost(self, connector, reason):
        pass

    def unregisterProtocol(self, p):
        """
        Called by protocols when they go away.
        """
        try:
            del self.protocols[p]
        except Exception:
            pass


@implementer(interfaces.IStreamClientEndpoint)
class SOCKS5ClientEndpoint(object):
    """
    SOCKS5 TCP client endpoint with an IPv4 configuration.
    """

    def __init__(self, reactor, sockhost, sockport,
                 host, port, optimistic, timeout=30, bindAddress=None):
        self._reactor = reactor
        self._sockhost = sockhost
        self._sockport = sockport
        self._host = host
        self._port = port
        self._optimistic = optimistic
        self._timeout = timeout
        self._bindAddress = bindAddress

    def connect(self, protocolFactory):
        try:
            wf = SOCKSv5ClientFactory(protocolFactory, self._host, self._port, self._optimistic)
            self._reactor.connectTCP(
                self._sockhost, self._sockport, wf,
                timeout=self._timeout, bindAddress=self._bindAddress)
            return wf._onConnection
        except Exception:
            return defer.fail()


@implementer(interfaces.IStreamClientEndpoint)
class TLSWrapClientEndpoint(object):
    """
    An endpoint which automatically starts TLS.

    code concept from https://github.com/habnabit/txsocksx

    :param contextFactory: A `ContextFactory`__ instance.
    :param wrappedEndpoint: The endpoint to wrap.
    __ http://twistedmatrix.com/documents/current/api/twisted.internet.protocol.ClientFactory.html
    """

    _wrapper = tls.TLSMemoryBIOFactory

    def __init__(self, contextFactory, wrappedEndpoint):
        self.contextFactory = contextFactory
        self.wrappedEndpoint = wrappedEndpoint

    def connect(self, fac):
        """Connect to the wrapped endpoint, then start TLS.
        The TLS negotiation is done by way of wrapping the provided factory
        with `TLSMemoryBIOFactory`__ during connection.
        :returns: A ``Deferred`` which fires with the same ``Protocol`` as
            ``wrappedEndpoint.connect(fac)`` fires with. If that ``Deferred``
            errbacks, so will the returned deferred.
        __ http://twistedmatrix.com/documents/current/api/twisted.protocols.tls.html
        """
        fac = self._wrapper(self.contextFactory, True, fac)
        return self.wrappedEndpoint.connect(fac).addCallback(self._unwrapProtocol)

    def _unwrapProtocol(self, proto):
        return proto.wrappedProtocol
