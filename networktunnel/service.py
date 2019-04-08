from twisted.application import service

from config import ConfigManager


class TunnelService(service.Service):
    def __init__(self):
        self.config = ConfigManager()

    def startService(self):
        super().startService()

    def stopService(self):
        super().stopService()
