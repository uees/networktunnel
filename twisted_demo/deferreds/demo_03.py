# 处理同步或异步结果

from twisted.internet import reactor, defer


def synchronousIsValidUser(user):
    '''
    Return true if user is a valid user, false otherwise
    '''
    return user in ["Alice", "Angus", "Agnes"]


def asynchronousIsValidUser(user):
    d = defer.Deferred()
    reactor.callLater(2, d.callback, synchronousIsValidUser(user))
    return d


def printResult(result):
    if result:
        print("User is authenticated")
    else:
        print("User is not authenticated")


# 同步版本的 authenticateUser
# def authenticateUser(isValidUser, user):
#    if isValidUser(user):
#        print("User is authenticated")
#    else:
#        print("User is not authenticated")


def authenticateUser(isValidUser, user):
    ''' 能同时处理同步和异步 isValidUser '''
    d = defer.maybeDeferred(isValidUser, user)
    d.addCallback(printResult)


if __name__ == "__main__":
    authenticateUser(asynchronousIsValidUser, 'Alice')  # User is authenticated
    authenticateUser(synchronousIsValidUser, 'Hehe')    # User is not authenticated
    reactor.callLater(4, reactor.stop)
    reactor.run()
