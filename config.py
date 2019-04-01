import os

import configparser

from settings import BASE_DIR


def get_config(filepath):
    parser = configparser.ConfigParser()
    parser.read(filepath)
    return parser


class ConfigFactory(object):
    config = None

    #
    #    -read(filename)     直接读取文件内容
    #    -sections()         得到所有的section，并以列表的形式返回
    #    -options(section)    得到该section的所有option
    #    -items(section)        得到该section的所有键值对
    #    -get(section,option)      得到section中option的值，返回为string类型
    #    -getint(section,option)    得到section中option的值，返回为int类型，还有相应的getboolean()和getfloat() 函数。
    def __init__(self):
        self.parser = get_config(os.path.join(BASE_DIR, 'default.conf'))

    @classmethod
    def get_config(cls):
        if cls.config is None:
            cls.config = cls()

        return cls.config

    def getTimeOut(self):
        return self.parser.getint('DEFAULT', 'timeout', fallback=30)

    def getConnectionsLimit(self):
        return self.parser.getint('DEFAULT', 'connectionslimit', fallback=100)

    def getListenInterface(self):
        return self.parser.get('DEFAULT', 'listeninterface', fallback='')

    def getSocksAuth(self):
        return self.parser.getboolean('DEFAULT', 'socksauth', fallback=True)

    def getAuthApi(self):
        return self.parser.get('DEFAULT', 'AuthApi', fallback='')

    def getAllowInsPeers(self):
        return self.parser.get('DEFAULT', 'AllowInsPeers', fallback='')

    def getAllowOutPeers(self):
        return self.parser.get('DEFAULT', 'AllowOutPeers', fallback='')

    def getProtocols(self):
        return self.parser.get('DEFAULT', 'Protocols', fallback='socks5')

    def getDebug(self):
        return self.parser.getboolean('DEFAULT', 'Debug', fallback=True)

    def getLogLevel(self):
        return self.parser.getint('DEFAULT', 'LogLevel', fallback=4)

    def getServerPort(self):
        return self.parser.getint('DEFAULT', 'ServerPort', fallback=6778)
