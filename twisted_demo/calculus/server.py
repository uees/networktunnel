#!/usr/bin/env python3
from twisted.protocols import basic
from twisted.internet import protocol
from twisted.python import log

from .base import Calculation


class CalculationProxy(object):
    def __init__(self):
        self.calc = Calculation()
        for m in ['add', 'subtract', 'multiply', 'divide']:
            setattr(self, 'remote_{}'.format(m), getattr(self.calc, m))


class RemoteCalculationProtocol(basic.LineReceiver):
    def __init__(self):
        self.proxy = CalculationProxy()

    def lineReceived(self, line):
        op, a, b = line.decode('utf-8').split()
        op = getattr(self.proxy, 'remote_{}'.format(op))
        try:
            a, b = Calculation.make_ints(a, b)
        except TypeError:
            log.err()
            self.sendLine(b"error")
        else:
            result = op(a, b)
            self.sendLine(str(result).encode('utf-8'))


class RemoteCalculationFactory(protocol.Factory):
    protocol = RemoteCalculationProtocol


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    reactor.listenTCP(0, RemoteCalculationFactory())
    reactor.run()


if __name__ == "__main__":
    main()
