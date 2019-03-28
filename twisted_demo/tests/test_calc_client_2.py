# python -m twisted.trial twisted_demo.tests.test_calc_client_2

from twisted.internet import task
from twisted.trial import unittest
from twisted.test import proto_helpers

from ..calculus.client_2 import RemoteCalculationClient, ClientTimeoutError


class ClientCalculationTestCase(unittest.TestCase):
    def setUp(self):
        self.tr = proto_helpers.StringTransportWithDisconnection()  # 该传输管理 loseConnection 并将其转发到它的 protocol。
        self.clock = task.Clock()
        self.proto = RemoteCalculationClient()
        self.tr.protocol = self.proto
        self.proto.callLater = self.clock.callLater
        self.proto.makeConnection(self.tr)

    def _test(self, operation, a, b, expected):
        d = getattr(self.proto, operation)(a, b)
        self.assertEqual(
            self.tr.value(),
            '{} {} {}\r\n'.format(operation, a, b).encode('utf-8')
        )
        self.tr.clear()
        d.addCallback(self.assertEqual, expected)
        self.proto.dataReceived("{}\r\n".format(expected, ).encode('utf-8'))
        return d

        # self.assertEqual(expected, self.successResultOf(d))

    def test_add(self):
        return self._test('add', 7, 6, 13)

    def test_subtract(self):
        return self._test('subtract', 82, 78, 4)

    def test_multiply(self):
        return self._test('multiply', 2, 8, 16)

    def test_divide(self):
        return self._test('divide', 14, 3, 4)

    def test_timeout(self):
        d = self.proto.add(9, 4)
        self.assertEqual(self.tr.value(), b'add 9 4\r\n')
        self.clock.advance(self.proto.timeOut)  # 模拟超时

        # self.failureResultOf(d).trap(ClientTimeoutError)
        return self.assertFailure(d, ClientTimeoutError)

    def test_timeoutConnectionLost(self):
        called = []

        def lost(arg):
            called.append(True)

        self.proto.connectionLost = lost

        d = self.proto.add(9, 4)
        self.assertEqual(self.tr.value(), b'add 9 4\r\n')
        self.clock.advance(self.proto.timeOut)

        def check(ignore):
            self.assertEqual(called, [True])

        return self.assertFailure(d, ClientTimeoutError).addCallback(check)

        # self.failureResultOf(d).trap(ClientTimeoutError)
        # self.assertEqual(called, [True])
