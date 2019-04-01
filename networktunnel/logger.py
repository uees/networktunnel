from config import config
from twisted.python import log


class LogMixin:
    @staticmethod
    def log(*message, **event):
        if config.getLogLevel() >= 3:
            log.msg(*message, **event)
