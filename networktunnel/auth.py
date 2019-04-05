from twisted.internet import defer

from config import ConfigFactory

from .errors import LoginAuthenticationFailed

config = ConfigFactory.get_config()


@defer.inlineCallbacks
def auth_token(token: str):
    if token == config.parser.get('DEFAULT', 'token'):
        yield True
    else:
        raise LoginAuthenticationFailed()
