import socket

from . import constants


# | 版本号(1字节) | 命令(1字节) | 保留(1字节) | 请求类型(1字节) | 地址(不定长) | 端口(2字节) |
# | ------------ | ---------- | ---------- | ------------- | ----------- | ---------- |
# | 固定为5       |            |            |             | 第1个字节为域名的长度 | -------|


def socks_domain_host(host: (str, bytes)):
    host = to_bytes(host)
    return b''.join((chr(len(host)), host))


def to_bytes(s: (str, bytes)):
    if type(s) == str:
        return s.encode('utf-8')
    return s


def to_str(s: (str, bytes)):
    if type(s) == bytes:
        return s.decode('utf-8')
    return s


def int32(x):
    if x > 0xFFFFFFFF or x < 0:
        x &= 0xFFFFFFFF

    if x > 0x7FFFFFFF:
        x = int(0x100000000 - x)
        if x < 0x80000000:
            return -x

        return -2147483648

    return x


def is_ip(address):
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            if type(address) != str:
                address = address.decode('utf-8')
            socket.inet_pton(family, address)
            return family
        except (TypeError, ValueError, OSError, IOError):
            pass

    return False


def get_method(methods: iter, choice: iter) -> int:
    result = constants.NO_ACCEPTABLE_METHODS
    for method in methods:
        if method in choice:
            result = method
            break

    return result
