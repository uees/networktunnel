import socket

from twisted.internet.protocol import Factory, Protocol
from twisted.names import dns
from twisted.names import client, server

CHANGE = 'example.com'
TO = '127.0.0.1'
TTL = 60


class DNSServerFactory(server.DNSServerFactory):
    def gotResolverResponse(self, response, protocol, message, address):
        ans, auth, add = response
        qname = message.queries[0].name.name
        if CHANGE in qname:
            for answer in ans:
                if answer.type != dns.A:
                    continue
                if CHANGE not in answer.name.name:
                    continue

                answer.payload.address = socket.inet_aton(TO)
                answer.payload.ttl = TTL

        args = (self, response, protocol, message, address)
        return server.DNSServerFactory.gotResolverResponse(*args)


verbosity = 0

resolver = client.Resolver(servers=[('8.8.8.8', 53)])
factory = DNSServerFactory(clients=[resolver], verbose=verbosity)
protocol = dns.DNSDatagramProtocol(factory)
factory.noisy = protocol.noisy = verbosity

if __name__ == "__main__":
    from twisted.internet import reactor

    reactor.listenUDP(53, protocol)
    reactor.listenTCP(53, factory)
    reactor.run()
