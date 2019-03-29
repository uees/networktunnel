from twisted.internet import protocol, reactor


class Echo(protocol.DatagramProtocol):

    def datagramReceived(self, data, addr):
        print("received {data} from {addr}".format(data=data, addr=addr))
        self.transport.write(data, addr)


reactor.listenUDP(9999, Echo())
reactor.run()
