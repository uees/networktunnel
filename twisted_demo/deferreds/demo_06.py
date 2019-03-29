# DeferredList 的一个常见用法是“连接”多个并行异步操作，如果所有操作都成功，则成功完成;
# 如果任何一个操作失败，则失败。在这种情况下，`twisted.internet.defer.gatherResults` 是一个有用的快捷方式:
from twisted.internet import defer

d1 = defer.Deferred()
d2 = defer.Deferred()
d = defer.gatherResults([d1, d2], consumeErrors=True)


def cbPrintResult(result):
    print(result)


d.addCallback(cbPrintResult)

d1.callback("one")
# nothing is printed yet; d is still awaiting completion of d2
d2.callback("two")
# printResult prints ["one", "two"]


# Chaining Deferreds
# chainDeferred(otherDeferred)
# This is the same as self.addCallbacks(otherDeferred.callback, otherDeferred.errback)
