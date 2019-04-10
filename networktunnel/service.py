import os

from twisted.application import service
from twisted.internet import reactor
from twisted.web import resource, server, static

from config import ConfigManager
from networktunnel.resource import PacResource
from settings import BASE_DIR


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
        super().startService()
        root = resource.Resource()
        root.putChild(b"pac", PacResource())
        root.putChild(b"gfwlist", static.File(os.path.join(BASE_DIR, 'gfwlist.txt')))
        factory = server.Site(root)
        self._port = reactor.listenTCP(self.portNum, factory)

    def stopService(self):
        super().stopService()
        return self._port.stopListening()
