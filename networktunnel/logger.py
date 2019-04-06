from twisted.python import log

from config import ConfigManager

config = ConfigManager()


class LogMixin:
    @staticmethod
    def log(*message, **event):
        if config.getLogLevel() >= 3:
            log.msg(*message, **event)
