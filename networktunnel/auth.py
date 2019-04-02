from twisted.internet import defer

from .errors import LoginAuthenticationFailed


@defer.inlineCallbacks
def auth_token(token):
    if token == 'a':
        yield True
    else:
        raise LoginAuthenticationFailed()
