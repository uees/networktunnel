# 回调链中的第一个回调将使用结果调用，第二个回调将使用第一个回调的结果调用，依此类推。

from twisted.internet import reactor, defer


class Getter:
    def __init__(self):
        self.d = None

    def gotResults(self, x):
        """
        The Deferred mechanism provides a mechanism to signal error
        conditions.  In this case, odd numbers are bad.

        This function demonstrates a more complex way of starting
        the callback chain by checking for expected results and
        choosing whether to fire the callback or errback chain
        """
        if self.d is None:
            print("Nowhere to put results")
            return

        d = self.d
        # 在使用结果或错误触发 Deferred 之前，将属性设置为 None，以便 Getter 实例不再有对将要触发的 Deferred 的引用
        # 这有几个好处。首先，它避免任何偶然的 Getter。gotResults将不小心多次触发相同的延迟(这将导致一个现成的callederror异常)。
        # 其次，它允许对那个 Deferred 调用 Getter 的回调。getDummyData(它为 d 属性设置了一个新值)不会引起问题。
        # 第三，通过消除引用循环，它使 Python 垃圾收集器的工作更容易。
        self.d = None
        if x % 2 == 0:
            d.callback(x*3)
        else:
            d.errback(ValueError("You used an odd number!"))

    def _toHTML(self, r):
        """
        This function converts r to HTML.

        It is added to the callback chain by getDummyData in
        order to demonstrate how a callback passes its own result
        to the next callback
        """
        return "Result: %s" % r

    def getDummyData(self, x):
        """
        The Deferred mechanism allows for chained callbacks.
        In this example, the output of gotResults is first
        passed through _toHTML on its way to printData.

        Again this function is a dummy, simulating a delayed result
        using callLater, rather than using a real asynchronous
        setup.
        """
        self.d = defer.Deferred()
        # simulate a delayed result by asking the reactor to schedule
        # gotResults in 2 seconds time
        reactor.callLater(2, self.gotResults, x)
        self.d.addCallback(self._toHTML)
        return self.d


def cbPrintData(result):
    print(result)


def ebPrintError(failure):
    import sys

    sys.stderr.write(str(failure))


# this series of callbacks and errbacks will print an error message
g = Getter()
d = g.getDummyData(3)
d.addCallback(cbPrintData)
d.addErrback(ebPrintError)

# this series of callbacks and errbacks will print "Result: 12"
g = Getter()
d = g.getDummyData(4)
d.addCallback(cbPrintData)
d.addErrback(ebPrintError)

reactor.callLater(4, reactor.stop)
reactor.run()
