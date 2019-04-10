import platform

if platform.system() == 'Linux':
    from twisted.internet import epollreactor

    epollreactor.install()

elif platform.system() == 'Windows':
    from twisted.internet import iocpreactor

    iocpreactor.install()

from twisted.application import internet, service
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.logger import ILogObserver
from twisted.python.logfile import DailyLogFile

from config import ConfigManager
from networktunnel.logger import textFileLogObserver
from networktunnel.remote_server import SocksServerFactory
from networktunnel.service import TunnelService
from settings import BASE_DIR

conf = ConfigManager().default


def get_application():
    logfile = DailyLogFile("networktunnel.log", BASE_DIR)

    application = service.Application("networktunnel")
    application.setComponent(ILogObserver, textFileLogObserver(logfile))

    top_service = service.MultiService()

    tunnel_service = TunnelService()
    tunnel_service.setServiceParent(top_service)

    port = conf.getint('remote', 'port', fallback=6778)
    tcp_service = internet.TCPServer(port, SocksServerFactory(reactor), interface='0.0.0.0')
    tcp_service.setServiceParent(top_service)

    top_service.setServiceParent(application)

    return application


def main():
    if conf.getboolean('remote', 'debug', fallback=True):
        from twisted.python import log
        import sys

        log.startLogging(sys.stdout)

    endpoint = TCP4ServerEndpoint(reactor, conf.getint('remote', 'ServerPort', fallback=6778))
    endpoint.listen(SocksServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
