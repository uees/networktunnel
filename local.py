import platform

if platform.system() == 'Linux':
    from twisted.internet import epollreactor

    epollreactor.install()

elif platform.system() == 'Windows':
    from twisted.internet import iocpreactor

    iocpreactor.install()

from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.application import service, internet
from twisted.logger import ILogObserver
from twisted.python.logfile import DailyLogFile

from config import ConfigManager
from settings import BASE_DIR
from networktunnel.logger import textFileLogObserver
from networktunnel.local_server import TransferServerFactory
from networktunnel.service import PacService

conf = ConfigManager().default


def get_application():
    logfile = DailyLogFile("local.log", BASE_DIR)

    application = service.Application("Local network tunnel")
    application.setComponent(ILogObserver, textFileLogObserver(logfile))

    top_service = service.MultiService()

    pac_service = PacService(conf.getint('local', 'pac_port', fallback=8080))
    pac_service.setServiceParent(top_service)

    port = conf.getint('local', 'port', fallback=1080)
    tcp_service = internet.TCPServer(port, TransferServerFactory(reactor), interface='0.0.0.0')
    tcp_service.setServiceParent(top_service)

    top_service.setServiceParent(application)

    return application


def main():
    if conf.getboolean('local', 'debug', fallback=True):
        from twisted.python import log
        import sys

        log.startLogging(sys.stdout)

    endpoint = TCP4ServerEndpoint(reactor, conf.getint('local', 'port'))
    endpoint.listen(TransferServerFactory(reactor))
    reactor.run()


if __name__ == "__main__":
    main()
