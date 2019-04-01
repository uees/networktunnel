AUTH_ANONYMOUS, AUTH_LOGIN, AUTH_TOKEN = 0x00, 0x01, 0x80  # 0x80 自定义 Login
AUTH_ERROR, AUTH_SUCCESS = 0x00, 0x01
ATYP_IPV4, ATYP_DOMAINNAME, ATYP_IPV6 = 0x01, 0x03, 0x04
CMD_CONNECT, CMD_BIND, CMD_UDP_ASSOCIATE = 0x01, 0x02, 0x03
NO_ACCEPTABLE_METHODS = 0xff
RSV = 0x00  # 保留字

SOCKS5_VER = 0x05
SOCKS5_GRANTED = SOCKS5_SUCCEEDED = 0x00
SOCKS5_GENERAL_FAILURE = SOCKS5_SERVER_FAILURE = 0x01
SOCKS5_REJECTED = SOCKS5_CONNECTION_NOT_ALLOWED_BY_RULESET = 0x02
SOCKS5_NETWORK_UNREACHABLE = 0x03
SOCKS5_HOST_UNREACHABLE = 0x04
SOCKS5_CONNECTION_REFUSED = 0x05
SOCKS5_TTL_EXPIRED = 0x06
SOCKS5_COMMAND_NOT_SUPPORTED = 0x07
SOCKS5_ADDRESS_TYPE_NOT_SUPPORTED = 0x08
