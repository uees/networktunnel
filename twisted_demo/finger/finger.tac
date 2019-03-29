# Read username, output from non-empty factory, drop connections
# Use deferreds, to minimize synchronicity assumptions

# twistd -ny twisted_demo\finger\finger.tac  # just like before
# twistd -y twisted_demo\finger\finger.tac   # daemonize, keep pid in twistd.pid
# twistd -y twisted_demo\finger\finger.tac --pidfile=finger.pid --rundir=/ --chroot=/var -l /var/log/finger.log


from twisted.application import service, strports
from twisted.internet import protocol, reactor, defer
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

    def __init__(self, users):
        self.users = users

    def getUser(self, user):
        return defer.succeed(self.users.get(user, b"No such user"))


application = service.Application('finger', uid=1, gid=1)
factory = FingerFactory({b'moshez': b'Happy and well'})
strports.service("tcp:79", factory, reactor=reactor).setServiceParent(
    service.IServiceCollection(application))
