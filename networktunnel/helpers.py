import socket
import struct
import binascii

from . import constants


# | 版本号(1字节) | 命令(1字节) | 保留(1字节) | 请求类型(1字节) | 地址(不定长) | 端口(2字节) |
# | ------------ | ---------- | ---------- | ------------- | ----------- | ---------- |
# | 固定为5       |            |            |             | 第1个字节为域名的长度 | -------|

def socks_domain_host(host):
    return chr(constants.ATYP_DOMAINNAME) + chr(len(host)) + host


def validate_socks4a_host(host):
    try:
        host = socket.inet_pton(socket.AF_INET, host)
    except socket.error:
        return
    if host[:3] == b'\0\0\0' and host[3] != b'\0':
        raise ValueError('SOCKS4a reserves addresses 0.0.0.1-0.0.0.255')


def to_bytes(s):
    if type(s) == str:
        return s.encode('utf-8')
    return s


def to_str(s):
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


def inet_ntop(family, ipstr):
    if family == socket.AF_INET:
        return to_bytes(socket.inet_ntoa(ipstr))

    if family == socket.AF_INET6:
        import re
        v6addr = ':'.join(('%02X%02X' % (ord(i), ord(j))).lstrip('0')
                          for i, j in zip(ipstr[::2], ipstr[1::2]))
        v6addr = re.sub('::+', '::', v6addr, count=1)
        return to_bytes(v6addr)


def inet_pton(family, addr):
    addr = to_str(addr)
    if family == socket.AF_INET:
        return socket.inet_aton(addr)

    if family == socket.AF_INET6:
        if '.' in addr:  # a v4 addr
            v4addr = addr[addr.rindex(':') + 1:]
            v4addr = socket.inet_aton(v4addr)
            v4addr = map(lambda x: ('%02X' % ord(x)), v4addr)
            v4addr.insert(2, ':')
            newaddr = addr[:addr.rindex(':') + 1] + ''.join(v4addr)
            return inet_pton(family, newaddr)

        dbyts = [0] * 8  # 8 groups
        grps = addr.split(':')
        for i, v in enumerate(grps):
            if v:
                dbyts[i] = int(v, 16)
            else:
                for j, w in enumerate(grps[::-1]):
                    if w:
                        dbyts[7 - j] = int(w, 16)
                    else:
                        break
                break
        return b''.join([chr(i // 256) + chr(i % 256) for i in dbyts])

    raise RuntimeError("What family?")


def patch_socket():
    if not hasattr(socket, 'inet_pton'):
        socket.inet_pton = inet_pton

    if not hasattr(socket, 'inet_ntop'):
        socket.inet_ntop = inet_ntop


patch_socket()


def is_ip(address):
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            if type(address) != str:
                address = address.decode('utf8')
            inet_pton(family, address)
            return family
        except (TypeError, ValueError, OSError, IOError):
            pass

    return False
