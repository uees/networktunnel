# -*- coding: utf-8 -*-

import os

from struct import pack, unpack
from socket import inet_ntoa, inet_aton
from configparser import ParsingError, RawConfigParser as ConfigParser

from twisted.application import internet, service
from twisted.internet import reactor
from twisted.protocols import policies, basic
from twisted.python import log
from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import threads


def rel(*x):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)


class FilePassword(object):
    """A file-based, text-based username/password database.

    Records in the datafile for this class are delimited by a particular
    string.  The username appears in a fixed field of the columns delimited
    by this string, as does the password.  Both fields are specifiable.
    """

    def __init__(self, files, delim=':'):
        """
        @type files: C{str}
        @param files: The name of the file from which to read username and
        password information.

        @type delim: C{str}
        @param delim: The field delimiter used in the file.
        """
        self.files = files
        self.delim = delim

    def _loadCredentials(self):
        try:
            files = open(self.files)
        except:
            log.err()
        else:
            for lines in files:
                lines = lines.rstrip()
                parts = lines.split(
                    self.delim, 1)
                if not len(parts) == 2:
                    continue
                yield parts[0], parts[1]

    def getUser(self, username):
        for u, p in self._loadCredentials():
            if u == username:
                return u, p
        raise KeyError(username)

    def request(self, username, password):
        try:
            u, p = self.getUser(username)
        except KeyError:
            return
        return p == password

    def __str__(self):
        return '<FilePassword [%s] 0x%02X>' % (self.files, id(self))


class ConfigFactory(object):

    def __init__(self):
        for file in ('',):
            if os.path.exists(file):
                break
        else:
            file = None
        if file is None:
            reactor.callWhenRunning(
                log.msg, 'No config loaded, use default settings'
            )
        else:
            with open(file, 'rb') as fp:
                parser = ConfigParser()
                parser.read_file(fp)
                for section in parser.sections():
                    for key, value in parser.items(section):
                        key, value = key.lower(), value.decode('utf8')
                        if section == 'general':
                            if key in (
                                    'timeout', 'connectionslimit',):
                                value and setattr(self, key, parser.getint(section, key))
                            elif key in (
                                    'socksauth',):
                                setattr(self, key, parser.getboolean(section, key))
                            elif key in (
                                    'usersfile', 'listeninterface',):
                                value and setattr(self, key, parser.get(section, key))
                            else:
                                raise ParsingError('unknown key "%s" in section "%s"' % (key, section))
                        else:
                            raise TypeError('unknown section "%s"' % (section))

    def getTimeOut(self):
        try:
            return self.timeout
        except:
            return 120

    def getConnectionsLimit(self):
        try:
            return self.connectionslimit
        except:
            return 100

    def getListenInterface(self):
        try:
            return str(self.listeninterface)
        except:
            return ''

    def getSocksAuth(self):
        try:
            return self.socksauth
        except:
            return True

    def getUsersFile(self):
        try:
            return str(self.usersfile)
        except:
            return rel('users')

    def getAllowInsPeers(self):
        pass

    def getAllowOutPeers(self):
        pass

    def getProtocols(self):
        return (('socks', 8891),)  # ( ('http', 8890), ('socks', 8891), )

    def getLogLevel(self):
        try:
            return self.loglevel
        except:
            return 1


class ProxyFactory(protocol.Factory):  # policies.LimitTotalConnectionsFactory):

    protocol = None

    @property
    def connectionLimit(self):
        return config.getConnectionsLimit()

    def registerProtocol(self, p):
        p.timeOut = config.getTimeOut()


class SocksProxyProtocol(policies.TimeoutMixin, protocol.Protocol):
    VERSION = (0x04, 0x05)

    STATE_IGNORED = 0x00
    STATE_METHODS = 0x01
    STATE_AUTHREQ = 0x02
    STATE_REQUEST = 0x03
    STATE_RECEIVE = 0x04

    DUMP_I = 0x01
    DUMP_O = 0x02

    AUTH_NONE = 0x00
    AUTH_USPW = 0x02
    AUTH_NSUP = 0xFF

    CODE_TCPC = 0x01
    CODE_TCPB = 0x02
    CODE_UPDA = 0x03

    TYPE_IPv4 = 0x01
    TYPE_IPv6 = 0x04
    TYPE_DOMN = 0x03

    class OProxyProtocol(protocol.Protocol):

        def __init__(self, father):
            self._father = father

        def connectionMade(self):

            if config.getLogLevel() >= 3:
                log.msg('Connection made', self.transport.getPeer())

            if self._father._buffered:
                self.write(self._father._buffered)
                # Clean buffer
                del self._father._buffered

            # Get peer
            peer = self.transport.getPeer()

            self._father.makeReply(0x00, port=peer.port, server=peer.host)
            self._father.setOutgoing(self)

            # Ok, set normal state
            self._father.setState(self._father.STATE_RECEIVE)

            # For FAST transfer
            self._father.dataReceived, self.dataReceived = (
                self.write, self._father.write
            )

            if config.getLogLevel() >= 3:
                # Ok session
                log.msg('Connect ok to "%s:%d" request from %s' % (
                    self.transport.getPeer().host, self.transport.getPeer().port, str(self._father.transport.getPeer())
                ))

        def connectionLost(self, reason):

            if config.getLogLevel() >= 3:
                log.msg('Connection lost', self.transport.getPeer(), reason.getErrorMessage()
                        )

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

    def __init__(self):
        self._authTypes = []
        self._authTypes.append(self.AUTH_NONE)
        self._authTypes.append(self.AUTH_USPW)

        self._buffered = ''
        self._selected = None

        # Set default state
        self._ssession = self.STATE_METHODS

        self._outgoing = None

    def timeoutConnection(self):

        if config.getLogLevel() >= 3:
            log.msg('Connection time', self.transport.getPeer())

        policies.TimeoutMixin.timeoutConnection(self)

    def connectionMade(self):

        if config.getLogLevel() >= 3:
            log.msg('Connection made', self.transport.getPeer())

        self.setTimeout(self.timeOut)

    def connectionLost(self, reason):

        if config.getLogLevel() >= 3:
            log.msg('Connection lost', self.transport.getPeer(), reason.getErrorMessage())

        self.setTimeout(None)

        # Remove outgoing
        if self._outgoing is not None and self._outgoing.transport:
            self._outgoing.transport.loseConnection()
        self._outgoing = None

    def dataReceived(self, data):

        # Normal transfer
        if self.isState(self.STATE_RECEIVE):
            return self._outgoing.write(data)

        self.resetTimeout()

        self._buffered = self._buffered + data

        if self.isState(self.STATE_IGNORED):
            return

        if self.isState(self.STATE_METHODS):
            if len(self._buffered) < 3:
                return

            version, count = unpack('!2B', self.readBytes(2))

            if version not in self.VERSION:
                if config.getLogLevel() >= 3:
                    log.msg('Wrong version from %s' % str(
                        self.transport.getPeer()))

                return self.transport.loseConnection()

            methods = unpack('!%db' % count, self.readBytes(count))

            for method in methods:
                if method in self._authTypes:
                    self._selected = method

                    # Ok, select method
                    break
                else:
                    self._selected = None

            if self._selected is None:
                responseCode = self.AUTH_NSUP  # NO ACCEPTABLE METHODS
            else:
                responseCode = self._selected

            if responseCode == self.AUTH_NONE:
                self.setState(self.STATE_REQUEST)
            elif responseCode == self.AUTH_USPW:
                self.setState(self.STATE_AUTHREQ)

            self.write(pack('!2B', version, responseCode))

            # Close connection, selected method not found
            if self._selected is None:
                return self.transport.loseConnection()
        elif self.isState(self.STATE_AUTHREQ):
            if len(self._buffered) < 3:
                return

            version, count = unpack('!2B', self.readBytes(2))

            if version not in self.VERSION:
                if config.getLogLevel() >= 3:
                    log.msg('Wrong version from %s' % str(
                        self.transport.getPeer()))

                return self.transport.loseConnection()

        elif self.isState(self.STATE_REQUEST):
            if len(self._buffered) < 4:
                return

            version, code, byte, type = unpack('!4B', self.readBytes(4))

            if version not in self.VERSION:
                if config.getLogLevel() >= 3:
                    log.msg('Wrong version from %s' % str(
                        self.transport.getPeer()))

                return self.transport.loseConnection()

            if type == self.TYPE_IPv4:
                server = inet_ntoa(self.readBytes(4))
            elif type == self.TYPE_DOMN:
                server = self.readBytes(ord(self.readBytes(1)))

                if not server:
                    return self.makeReply(code=0x01, end=True)
            else:
                return self.makeReply(code=0x08, end=True)  # Address type not supported

            port = unpack('!H', self.readBytes(2))[0]

            if code == self.CODE_TCPC:

                # Try connect to server
                protocol.ClientCreator(reactor, self.OProxyProtocol, self).connectTCP(server, port).addErrback(
                    lambda result, self=self: self.makeReply(code=0x04, end=True))

            else:
                return self.makeReply(code=0x01, end=True)

            self.setState(self.STATE_IGNORED)
        else:

            if config.getLogLevel() >= 3:
                log.msg('%s state lost' % (
                    self
                ))
            return self.transport.loseConnection()

    def readBytes(self, bytes=None):
        # Set all bytes
        if bytes is None:
            bytes = len(self._buffered)

        data, self._buffered = (
            self._buffered[:bytes], self._buffered[bytes:])

        return data

    def makeReply(self, code, port=0, server=None, end=False):
        # Write reply
        self.write(pack('!4B', 0x05, code, 0x00, self.TYPE_IPv4) + (
                inet_aton(server or '0.0.0.0') + pack('!H', port)))

        # Close connection
        if end:
            self.transport.loseConnection()

    def isState(self, state):
        return self._ssession == state

    def setState(self, state):
        self._ssession = state

    def write(self, data):
        '''
        if config.getLogLevel() >= 4:
            log.msg('%s send %r' % (
                self, data
            ))
        '''
        self.transport.write(data)

    def setOutgoing(self, outgoing):
        self._outgoing = outgoing


class SocksProxyFactory(ProxyFactory):
    protocol = SocksProxyProtocol


config = ConfigFactory()

if config.getUsersFile():
    authChecker = FilePassword(files=config.getUsersFile())
else:
    authChecker = None

application = service.Application('ARX-Proxy')  # create the Application

for protocols, port in config.getProtocols():
    factory = locals().get(protocols.capitalize() + 'ProxyFactory')

    # Start listen
    if factory is not None:
        internet.TCPServer(port, factory()).setServiceParent(application)
