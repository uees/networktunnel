import socket
import struct

from . import constants, errors


# | 版本号(1字节) | 命令(1字节) | 保留(1字节) | 请求类型(1字节) | 地址(不定长) | 端口(2字节) |
# | ------------ | ---------- | ---------- | ------------- | ----------- | ---------- |
# | 固定为5       |            |            |             | 第1个字节为域名的长度 | -------|


def socks_domain_host(host: (str, bytes)) -> bytes:
    host = to_bytes(host)
    return b''.join((struct.pack('!B', len(host)), host))


def parse_address(atype: int, data: bytes) -> tuple:
    cur = 4
    if atype == constants.ATYP_DOMAINNAME:
        domain_len = ord(data[cur:cur + 1])
        cur += 1

        domain = data[cur:cur + domain_len].decode()
        cur += domain_len

    elif atype == constants.ATYP_IPV4:
        domain = socket.inet_ntop(socket.AF_INET, data[cur:cur + 4])
        cur += 4

    elif atype == constants.ATYP_IPV6:
        domain = socket.inet_ntop(socket.AF_INET6, data[cur:cur + 16])
        cur += 16

    else:
        raise errors.AddressNotSupported("Unknown address type!")

    port = struct.unpack('!H', data[cur:cur + 2])[0]

    return domain, port


def to_bytes(s: (str, bytes)) -> bytes:
    if isinstance(s, str):
        return s.encode()
    return s


def to_str(s: (str, bytes)) -> str:
    if isinstance(s, bytes):
        return s.decode()
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
