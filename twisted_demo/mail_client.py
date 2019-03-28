#!/usr/bin/env python3

from __future__ import print_function

import sys

from twisted.internet import defer, endpoints, protocol, task
from twisted.mail import imap4
from twisted.python import failure


@defer.inlineCallbacks
def main(reactor, username=b"alice", password=b"secret", strport="tls:example.com:993"):
    endpoint = endpoints.clientFromString(reactor, strport)
    factory = protocol.Factory.forProtocol(imap4.IMAP4Client)
    try:
        client = yield endpoint.connect(factory)
        yield client.login(username, password)
        yield client.select('INBOX')
        info = yield client.fetchEnvelope(imap4.MessageSet(1))
        print('First message subject:', info[1]['ENVELOPE'][1])
    except Exception:
        print("IMAP4 client interaction failed")
        failure.Failure().printTraceback()


if __name__ == "__main__":
    task.react(main, sys.argv[1:])
