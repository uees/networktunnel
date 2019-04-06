from twisted.internet.endpoints import TCP4ServerEndpoint

from config import ConfigManager
from networktunnel.remote_server import SocksServerFactory


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    config = ConfigManager()
    endpoint = TCP4ServerEndpoint(reactor, config.getServerPort())
    endpoint.listen(SocksServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
