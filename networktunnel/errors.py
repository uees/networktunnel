# -*- coding: utf-8 -*-

from networktunnel import constants as c


class ParsingError(Exception):
    """
    die 0x00
    """


class InvalidServerVersion(Exception):
    """
    die 0x00
    """


class StateError(Exception):
    """
    There was a problem with the State.
    """
    code = c.SOCKS5_SERVER_FAILURE


class SOCKSError(Exception):
    code = c.SOCKS5_SERVER_FAILURE


class ConnectionError(SOCKSError):
    pass


class LoginAuthenticationFailed(SOCKSError):
    code = c.AUTH_ERROR


class NoAcceptableMethods(SOCKSError):
    """
    No Acceptable Methods ( FF )
    """
    code = c.NO_ACCEPTABLE_METHODS


class ServerFailure(SOCKSError):
    """
    General SOCKS server failure ( 1 )
    """
    code = c.SOCKS5_SERVER_FAILURE


class ConnectionNotAllowed(SOCKSError):
    """
    Connection not allowed ( 2 )
    """
    code = c.SOCKS5_CONNECTION_NOT_ALLOWED_BY_RULESET


class NetworkUnreachable(SOCKSError):
    """
    Network unreachable ( 3 )
    """
    code = c.SOCKS5_NETWORK_UNREACHABLE


class HostUnreachable(SOCKSError):
    """
    Host unreachable ( 4 )
    """
    code = c.SOCKS5_HOST_UNREACHABLE


class ConnectionRefused(SOCKSError):
    """
    Connection refused ( 5 )
    """
    code = c.SOCKS5_CONNECTION_REFUSED


class TTLExpired(SOCKSError):
    """
    TTL expired ( 6 )
    """
    code = c.SOCKS5_TTL_EXPIRED


class CommandNotSupported(SOCKSError):
    """
    Command Not Supported ( 7 )
    """
    code = c.SOCKS5_COMMAND_NOT_SUPPORTED


class AddressNotSupported(SOCKSError):
    """
    Address type not supported ( 8 )
    """
    code = c.SOCKS5_ADDRESS_TYPE_NOT_SUPPORTED
