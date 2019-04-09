from twisted.application import service
from twisted.internet import reactor
from twisted.web import resource, server

from config import ConfigManager
from networktunnel.resource import PacResource


class TunnelService(service.Service):
    def __init__(self):
        self.config = ConfigManager()

    def startService(self):
        super().startService()

    def stopService(self):
        super().stopService()


class PacService(service.Service):
    _port = None

    def __init__(self, portNum):
        self.portNum = portNum

    def startService(self):
        root = resource.Resource()
        root.putChild(b"pac", PacResource())
        factory = server.Site(root)
        self._port = reactor.listenTCP(self.portNum, factory)

    def stopService(self):
        return self._port.stopListening()
