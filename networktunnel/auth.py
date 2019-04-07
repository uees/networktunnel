from twisted.internet import defer

from config import ConfigManager
from networktunnel.errors import LoginAuthenticationFailed

conf = ConfigManager().default


@defer.inlineCallbacks
def auth_token(token: str):
    if token == conf.get('remote', 'token'):
        yield True
    else:
        raise LoginAuthenticationFailed()
