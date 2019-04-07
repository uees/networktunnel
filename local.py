from twisted.internet.endpoints import TCP4ServerEndpoint

from config import ConfigManager
from networktunnel.local_server import TransferServerFactory


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    cfg = ConfigManager().default
    endpoint = TCP4ServerEndpoint(reactor, cfg.getint('local', 'port'))
    endpoint.listen(TransferServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
