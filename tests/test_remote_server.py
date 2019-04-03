# python -m twisted.trial tests.test_remote_server
import socket
import struct

from twisted.internet import reactor
from twisted.trial import unittest
from twisted.test import proto_helpers

from networktunnel import constants
from networktunnel.helpers import socks_domain_host
from networktunnel.remote_server import RemoteSocksV5ServerFactory, RemoteSocksV5Server as Socks5


class RemoteSocksV5ServerTestCase(unittest.TestCase):

    def setUp(self):
        # from twisted.internet.base import DelayedCall
        # DelayedCall.debug = True

        factory = RemoteSocksV5ServerFactory(reactor)
        self.proto = factory.buildProtocol(("127.0.0.1", 1080))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def _test_negotiate_methods_right(self):
        self.proto.set_state(Socks5.STATE_METHODS)
        self.proto.dataReceived(struct.pack('!BBB', 0x05, 0x01, 0x80))
        self.assertEqual(self.tr.value(), struct.pack('!BB', 0x05, 0x80))
        self.assertTrue(self.proto.is_state(Socks5.STATE_AUTH))
        self.tr.clear()

    def _test_negotiate_methods_error(self):
        self.proto.set_state(Socks5.STATE_METHODS)
        self.proto.dataReceived(struct.pack('!BBB', 5, 1, 0x01))
        self.assertEqual(self.tr.value(), struct.pack('!BB', 5, 0xff))
        self.assertTrue(self.proto.is_state(Socks5.STATE_IGNORED))
        self.tr.clear()

    def _test_err_request(self, state: int):
        self.proto.set_state(state)
        self.proto.dataReceived(struct.pack('!B', 4))
        self.assertEqual(self.tr.value(), struct.pack('!B', 0))
        self.tr.clear()

        self.proto.set_state(state)
        self.proto.dataReceived(struct.pack('!BBB', 4, 1, 0x00))
        self.assertEqual(self.tr.value(), struct.pack('!B', 0))
        self.tr.clear()

        self.assertTrue(self.proto.is_state(Socks5.STATE_IGNORED))

    def test_negotiate_methods(self):
        self._test_err_request(Socks5.STATE_METHODS)
        self._test_negotiate_methods_right()
        self._test_negotiate_methods_error()

    def test_auth(self):
        self.proto.set_state(Socks5.STATE_AUTH)
        self.proto._auth_method = constants.AUTH_TOKEN
        self.proto.dataReceived(struct.pack('!BBB', 0x05, 0x01, 0x61))  # 0x61 = 97 is 'a'
        self.assertEqual(self.tr.value(), struct.pack('!BB', 5, 1))
        self.assertTrue(self.proto.is_state(Socks5.STATE_COMMAND))

    def test_not_supported_cmd(self):
        self.proto.set_state(Socks5.STATE_COMMAND)
        request = b''.join([
            struct.pack('!4B', 5, 6, constants.RSV, constants.ATYP_IPV4),
            b''.join([socket.inet_aton('127.0.0.1'), struct.pack('!H', 1080)])
        ])
        self.proto.dataReceived(request)
        self.assertEqual(self.tr.value()[:2], struct.pack('!BB', 5, constants.SOCKS5_COMMAND_NOT_SUPPORTED))

    def test_cmd_conn(self):
        self.proto.set_state(Socks5.STATE_COMMAND)
        #request = b''.join([
        #    struct.pack('!4B', 5, constants.CMD_CONNECT, constants.RSV, constants.ATYP_DOMAINNAME),
        #    b''.join([socks_domain_host('www.baidu.com'), struct.pack('!H', 80)])
        #])

        request = b''.join([
            struct.pack('!4B', 5, constants.CMD_CONNECT, constants.RSV, constants.ATYP_IPV4),
            b''.join([socket.inet_aton('127.0.0.1'), struct.pack('!H', 6000)])
        ])

        self.proto.dataReceived(request)
        print(self.tr.value())
        # self.assertEqual(self.tr.value()[:2], struct.pack('!BB', 5, constants.SOCKS5_SUCCEEDED))
