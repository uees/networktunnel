# 回调例子

from twisted.internet import reactor, defer
from twisted.python import log


def getDummyData(inputData):
    """
    该函数是一个模拟延迟结果的虚拟函数
    返回一个Deferred，它将触发该结果。
    """
    print('getDummyData called')
    deferred = defer.Deferred()
    # simulate a delayed result by asking the reactor to fire the
    # Deferred in 2 seconds time with the result inputData * 3
    reactor.callLater(2, deferred.callback, inputData * 3)
    return deferred


def cbPrintData(result):
    """
    Data handling function to be added as a callback: handles the
    data by printing the result
    """
    print('Result received: {}'.format(result))


deferred = getDummyData(3)
deferred.addCallback(cbPrintData)

# Make sure errors get logged
deferred.addErrback(log.err)

# manually set up the end of the process by asking the reactor to
# stop itself in 4 seconds time
reactor.callLater(4, reactor.stop)
# start up the Twisted reactor (event loop handler) manually
print('Starting the reactor')
reactor.run()
