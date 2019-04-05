import os
from twisted.internet.endpoints import TCP4ServerEndpoint

from config import get_config
from settings import BASE_DIR
from networktunnel.local_server import ProxyFactory

cfg = get_config(os.path.join(BASE_DIR, 'local.conf'))


def main():
    from twisted.internet import reactor
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)
    endpoint = TCP4ServerEndpoint(reactor, cfg.getint('default', 'port'))
    endpoint.listen(ProxyFactory(reactor, cfg.get('default', 'key')))
    reactor.run()


if __name__ == "__main__":
    main()
