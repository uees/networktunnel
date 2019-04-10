from twisted.logger import (FileLogObserver, formatEventAsClassicLogText,
                            formatTime, timeFormatRFC3339)

from config import ConfigManager

config = ConfigManager()


def textFileLogObserver(outFile, timeFormat=timeFormatRFC3339):
    config_level = config.getLogLevel()

    def formatEvent(event):
        log_level = event.get('log_level')

        if log_level is not None and log_level < config_level:
            # 比配置级别低的日志直接丢弃
            return None

        return formatEventAsClassicLogText(
            event, formatTime=lambda e: formatTime(e, timeFormat)
        )

    return FileLogObserver(outFile, formatEvent)
