from twisted.python import log

from config import ConfigFactory


class LogMixin:
    @staticmethod
    def log(*message, **event):
        if ConfigFactory.get_config().getLogLevel() >= 3:
            log.msg(*message, **event)
