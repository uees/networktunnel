import socket
import struct

from networktunnel import constants, errors

# +----+------+----------+
# | VER | ULEN | UTOKEN  |
# +----+------+----------+
# |  1 |  1   | 1 to 255 |
# +----+------+----------+
#
# +----+---------+
# | VER | STATUS |
# +-----+--------+
# |  1  |  1     |
# +-----+--------+
#
# +----+-----+-------+------+----------+----------+
# |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
# +----+-----+-------+------+----------+----------+
# | 1  |  1  | X'00' |  1   | Variable |    2     |
# +----+-----+-------+------+----------+----------+
#
# +----+-----+-------+------+----------+----------+
# | VER | REP | RSV | ATYP | BND.ADDR | BND.PORT |
# +----+-----+-------+------+----------+----------+
# |  1 |  1  | X'00' |  1   | Variable | 2       |
# +----+-----+-------+------+----------+----------+
#
# +----+------+------+----------+----------+----------+
# | RSV | FRAG | ATYP | DST.ADDR | DST.PORT | DATA    |
# +----+------+------+----------+----------+----------+
# |  2 |  1   |   1  | Variable |   2      | Variable |
# +----+------+------+----------+----------+----------+


def socks_domain_host(host: (str, bytes)) -> bytes:
    host = to_bytes(host)
    return b''.join((struct.pack('!B', len(host)), host))


def parse_address(atyp: int, data: bytes, cur: int = 4) -> tuple:
    if atyp == constants.ATYP_DOMAINNAME:
        domain_len = ord(data[cur:cur + 1])
        cur += 1

        domain = data[cur:cur + domain_len].decode()
        cur += domain_len

    elif atyp == constants.ATYP_IPV4:
        domain = socket.inet_ntop(socket.AF_INET, data[cur:cur + 4])
        cur += 4

    elif atyp == constants.ATYP_IPV6:
        domain = socket.inet_ntop(socket.AF_INET6, data[cur:cur + 16])
        cur += 16

    else:
        raise errors.AddressNotSupported("Unknown address type!")

    port = struct.unpack('!H', data[cur:cur + 2])[0]

    return domain, port


def udp_frame_header_length(atyp: int, data: bytes):
    if atyp == constants.ATYP_DOMAINNAME:
        domain_len = ord(data[4:5])
        addr_len = domain_len + 1
    elif atyp == constants.ATYP_IPV4:
        addr_len = 4
    elif atyp == constants.ATYP_IPV6:
        addr_len = 16
    else:
        raise errors.AddressNotSupported("Unknown address type!")

    header_len = 6 + addr_len

    return header_len


def parse_udp_frame(data: bytes) -> tuple:
    # rsv 保留字 忽略
    rsv, frag, atyp = struct.unpack('!HBB', data[0:4])
    host, port = parse_address(atyp, data)
    header_len = udp_frame_header_length(atyp, data)
    return frag, atyp, host, port, data[header_len:]


def create_udp_frame(frag: int, atyp: int, host: (str, bytes), port: int, data: bytes) -> bytes:
    if atyp == constants.ATYP_DOMAINNAME:
        addr = socks_domain_host(host)
    elif atyp == constants.ATYP_IPV4 or atyp == constants.ATYP_IPV6:
        addr = host
    else:
        raise errors.AddressNotSupported("Unknown address type!")

    return b''.join([
        struct.pack('!HBB', 0, frag, atyp),
        addr,
        struct.pack('!H', port),
        data
    ])


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
