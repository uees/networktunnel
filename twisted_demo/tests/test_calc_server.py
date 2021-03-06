# python -m twisted.trial twisted_demo.tests.test_calc_server

from twisted.trial import unittest
from twisted.test import proto_helpers

from ..calculus.server import RemoteCalculationFactory


class RemoteCalculationTestCase(unittest.TestCase):

    def setUp(self):
        factory = RemoteCalculationFactory()
        self.proto = factory.buildProtocol(("127.0.0.1", 0))
        self.tr = proto_helpers.StringTransport()
        self.proto.makeConnection(self.tr)

    def _test(self, operation, a, b, expected):
        self.proto.dataReceived('{} {} {}\r\n'.format(operation, a, b).encode('utf-8'))
        self.assertEqual(int(self.tr.value()), expected)

    def test_add(self):
        return self._test('add', 7, 6, 13)

    def test_subtract(self):
        return self._test('subtract', 82, 78, 4)

    def test_multiply(self):
        return self._test('multiply', 2, 8, 16)

    def test_divide(self):
        return self._test('divide', 14, 3, 4)

    def test_invalidParameters(self):
        self.proto.dataReceived(b'add foo bar\r\n')
        self.assertEqual(self.tr.value(), b"error\r\n")
        errors = self.flushLoggedErrors(TypeError)  # Handling logged errors
        self.assertEqual(len(errors), 1)
