from twisted.internet.endpoints import TCP4ServerEndpoint

from networktunnel.remote_server import RemoteSocksV5ServerFactory


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    endpoint = TCP4ServerEndpoint(reactor, 1080)
    endpoint.listen(RemoteSocksV5ServerFactory())
    reactor.run()


if __name__ == "__main__":
    main()
