import platform

from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint

from config import ConfigManager
from networktunnel.remote_server import SocksServerFactory

if platform.system() == 'Linux':
    from twisted.internet import epollreactor

    epollreactor.install()

elif platform.system() == 'Windows':
    from twisted.internet import iocpreactor

    iocpreactor.install()


def main():
    conf = ConfigManager().default
    if conf.getboolean('remote', 'debug', True):
        from twisted.python import log
        import sys

        log.startLogging(sys.stdout)

    endpoint = TCP4ServerEndpoint(reactor, conf.getint('remote', 'ServerPort', fallback=6778))
    endpoint.listen(SocksServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
