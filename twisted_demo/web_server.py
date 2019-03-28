#!/usr/bin/env python3

from twisted.internet import endpoints, reactor
from twisted.web import resource, server


class Counter(resource.Resource):
    isLeaf = True
    numberRequests = 0

    def render_GET(self, request):
        self.numberRequests += 1
        request.setHeader(b"content-type", b"text/plain")
        content = u"I am request #{}\n".format(self.numberRequests)
        return content.encode("ascii")


if __name__ == "__main__":
    endpoints.serverFromString(reactor, "tcp:8080").listen(server.Site(Counter()))

    reactor.run()
