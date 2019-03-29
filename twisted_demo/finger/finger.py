from twisted.internet import defer, endpoints, protocol, reactor, utils
from twisted.protocols import basic


class FingerProtocol(basic.LineReceiver):

    def connectionMade(self):
        self.sendLine(b"Wellcome client!")
        self.transport.write(b"please login:\r\n")

    def lineReceived(self, user):
        d = self.factory.getUser(user)

        def onError(err):
            return 'Internal error in server'

        d.addErrback(onError)

        def writeResponse(message):
            self.transport.write(message + b'\r\n')
            self.transport.loseConnection()

        d.addCallback(writeResponse)


class FingerFactory(protocol.ServerFactory):
    protocol = FingerProtocol

    def __init__(self, users=None):
        self.users = users

    def getUser(self, user):
        # user = self.users.get(user, "No such user")
        # return defer.succeed(user)
        return utils.getProcessOutput(b"finger", [user])


# users = {'moshez': 'Happy and well'}

fingerEndpoint = endpoints.serverFromString(reactor, "tcp:1079")
fingerEndpoint.listen(FingerFactory())
reactor.run()
