import os
import configparser

from twisted.logger import LogLevel

from settings import BASE_DIR


class ConfigManager(object):
    _config = {}

    #
    #    -read(filename)     直接读取文件内容
    #    -sections()         得到所有的section，并以列表的形式返回
    #    -options(section)    得到该section的所有option
    #    -items(section)        得到该section的所有键值对
    #    -get(section,option)      得到section中option的值，返回为string类型
    #    -getint(section,option)    得到section中option的值，返回为int类型，还有相应的getboolean()和getfloat() 函数。
    def __init__(self, default='default.conf'):
        self.default = self.get_config(os.path.join(BASE_DIR, default))

    @classmethod
    def load_config(cls, filepath):
        parser = configparser.ConfigParser()
        parser.read(filepath)
        cls._config.update({filepath: parser})
        return parser

    @classmethod
    def get_config(cls, filename):
        parser = cls._config.get(filename)

        if not parser:
            parser = cls.load_config(filename)

        return parser

    def getTimeOut(self):
        return self.default.getint('default', 'timeout', fallback=30)

    def getLogLevel(self):
        return LogLevel.levelWithName(self.default.get('default', 'loglevel', fallback='debug'))
