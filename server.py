from twisted.internet.endpoints import TCP4ServerEndpoint

from config import ConfigFactory
from networktunnel.remote_server import RemoteSocksV5ServerFactory

config = ConfigFactory.get_config()


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    endpoint = TCP4ServerEndpoint(reactor, config.getServerPort())
    endpoint.listen(RemoteSocksV5ServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
