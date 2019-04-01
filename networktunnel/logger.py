from config import ConfigFactory
from twisted.python import log


class LogMixin:
    @staticmethod
    def log(*message, **event):
        if ConfigFactory.get_config().getLogLevel() >= 3:
            log.msg(*message, **event)
