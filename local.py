import platform

if platform.system() == 'Linux':
    from twisted.internet import epollreactor

    epollreactor.install()

elif platform.system() == 'Windows':
    from twisted.internet import iocpreactor

    iocpreactor.install()

from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor

from config import ConfigManager
from networktunnel.local_server import TransferServerFactory


def main():
    cfg = ConfigManager().default

    if cfg.getboolean('local', 'debug', fallback=True):
        from twisted.python import log
        import sys

        log.startLogging(sys.stdout)

    endpoint = TCP4ServerEndpoint(reactor, cfg.getint('local', 'port'))
    endpoint.listen(TransferServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
