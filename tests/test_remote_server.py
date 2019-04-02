# python -m twisted.trial tests.test_remote_server

import struct

from twisted.trial import unittest
from twisted.test import proto_helpers

from networktunnel.remote_server import RemoteSocksV5ServerFactory, RemoteSocksV5Server as Socks5


class RemoteSocksV5ServerTestCase(unittest.TestCase):

    def setUp(self):
        # from twisted.internet.base import DelayedCall
        # DelayedCall.debug = True

        factory = RemoteSocksV5ServerFactory()
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
        self.proto.dataReceived(struct.pack('!BBB', 5, 1, 0x00))
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

    def test_connect(self):
        self._test_err_request(Socks5.STATE_METHODS)
        self._test_negotiate_methods_right()
        self._test_negotiate_methods_error()
