from .errors import LoginAuthenticationFailed


def auth_token(token):
    if not token:
        raise LoginAuthenticationFailed()

    return True
