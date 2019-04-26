import sys
import argparse
from urllib.parse import urlparse

from twisted.python import log as _log
from twisted.web.http import HTTPFactory
from twisted.internet import ssl, reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.web.proxy import Proxy, ProxyRequest
from twisted.logger import Logger

log = Logger()


class ConnectProxyRequest(ProxyRequest):
    """HTTP ProxyRequest handler (factory) that supports CONNECT"""

    connectedProtocol = None

    def process(self):
        if self.method == 'CONNECT':
            self.processConnectRequest()
        else:
            super().process()

    def fail(self, message, body):
        self.setResponseCode(501, message)
        self.responseHeaders.addRawHeader("Content-Type", "text/html")
        self.write(body)
        self.finish()

    def splitHostPort(self, hostport, default_port):
        port = default_port
        parts = hostport.split(':', 1)
        if len(parts) == 2:
            try:
                port = int(parts[1])
            except ValueError:
                pass
        return parts[0], port

    def processConnectRequest(self):
        parsed = urlparse(self.uri)
        default_port = self.ports.get(parsed.scheme)

        host, port = self.splitHostPort(parsed.netloc or parsed.path,
                                        default_port)
        if port is None:
            self.fail("Bad CONNECT Request",
                      "Unable to parse port from URI: %s" % repr(self.uri))
            return

        clientFactory = ConnectProxyClientFactory(host, port, self)

        self.reactor.connectTCP(host, port, clientFactory)


class ConnectProxy(Proxy):
    """HTTP Server Protocol that supports CONNECT"""
    requestFactory = ConnectProxyRequest
    connectedRemote = None

    def requestDone(self, request):
        if request.method == 'CONNECT' and self.connectedRemote is not None:
            self.connectedRemote.connectedClient = self

        super().requestDone(request)

    def connectionLost(self, reason):
        if self.connectedRemote is not None:
            self.connectedRemote.transport.loseConnection()

        super().connectionLost(reason)

    def dataReceived(self, data):
        if self.connectedRemote is None:
            log.info('self.connectedRemote is None')
            super().dataReceived(data)
        else:
            log.info('Once proxy is connected, forward all bytes received')
            # Once proxy is connected, forward all bytes received
            # from the original client to the remote server.
            self.connectedRemote.transport.write(data)


class ConnectProxyClient(Protocol):
    connectedClient = None

    def connectionMade(self):
        self.factory.request.channel.connectedRemote = self
        self.factory.request.setResponseCode(200, "CONNECT OK")
        self.factory.request.setHeader('X-Connected-IP', self.transport.realAddress[0])
        self.factory.request.setHeader('Content-Length', '0')
        self.factory.request.finish()

    def connectionLost(self, reason):
        if self.connectedClient is not None:
            self.connectedClient.transport.loseConnection()

    def dataReceived(self, data):
        if self.connectedClient is not None:
            # Forward all bytes from the remote server back to the
            # original connected client
            self.connectedClient.transport.write(data)
        else:
            log.info("UNEXPECTED DATA RECEIVED: {data!r}", data=data)


class ConnectProxyClientFactory(ClientFactory):
    protocol = ConnectProxyClient

    def __init__(self, host, port, request):
        self.request = request
        self.host = host
        self.port = port

    def clientConnectionFailed(self, connector, reason):
        self.request.fail("Gateway Error", str(reason))


if __name__ == '__main__':
    _log.startLogging(sys.stdout)

    ap = argparse.ArgumentParser()
    ap.add_argument('port', default=8090, nargs='?', type=int)
    ap.add_argument('--ssl-cert', type=str)
    ap.add_argument('--ssl-key', type=str)
    ns = ap.parse_args()

    factory = HTTPFactory()
    factory.protocol = ConnectProxy

    if ns.ssl_key and not ns.ssl_cert:
        log.info("--ssl-key must be used with --ssl-cert")
        sys.exit(1)
    if ns.ssl_cert:
        with open(ns.ssl_cert, 'rb') as fp:
            ssl_cert = fp.read()
        if ns.ssl_key:
            from OpenSSL import crypto
            with open(ns.ssl_key, 'rb') as fp:
                ssl_key = fp.read()
            certificate = ssl.PrivateCertificate.load(
                    ssl_cert,
                    ssl.KeyPair.load(ssl_key, crypto.FILETYPE_PEM),
                    crypto.FILETYPE_PEM)
        else:
            certificate = ssl.PrivateCertificate.loadPEM(ssl_cert)
        reactor.listenSSL(ns.port, factory, certificate.options())
    else:
        reactor.listenTCP(ns.port, factory)
    reactor.run()
