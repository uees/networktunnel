from twisted.internet import defer

from .errors import LoginAuthenticationFailed


@defer.inlineCallbacks
def auth_token(token):
    if not token:
        raise LoginAuthenticationFailed()

    return True
