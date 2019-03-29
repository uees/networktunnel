# Creating Cancellable Deferreds: Custom Cancellation Functions

import random

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol


class HTTPClient(Protocol):
    def request(self, method, path):
        self.resultDeferred = Deferred(
            lambda ignore: self.transport.abortConnection())
        request = b"%s %s HTTP/1.0\r\n\r\n" % (method, path)
        self.transport.write(request)
        return self.resultDeferred

    def dataReceived(self, data):
        # ... parse HTTP response ...
        # ... eventually call self.resultDeferred.callback() ...
        pass

# Now if someone calls cancel() on the Deferred returned from HTTPClient.request(),
# the HTTP request will be cancelled (assuming it’s not too late to do so). Care should
# be taken not to callback() a Deferred that has already been cancelled.


# 超时是一种特殊的取消情况。假设我们有一个表示任务的延迟，这个任务可能会花费很长时间。
# 我们想给这个任务设定一个上限，所以我们想要延迟到X秒以后。一个方便的API是Deferred.addTimeout。
# 默认情况下，如果延迟的对象在超时秒内没有触发(使用errback或回调)，那么它将失败，并带有TimeoutError。

def f():
    return "Hopefully this will be called in 3 seconds or less"


def logTimeout(result, timeout):
    print("Got {0!r} but actually timed out after {1} seconds".format(
        result, timeout))
    return result + " (timed out)"


def main(reactor):
    delay = random.uniform(1, 5)

    def called(result):
        print("{0} seconds later:".format(delay), result)

    d = task.deferLater(reactor, delay, f)
    d.addTimeout(3, reactor, onTimeoutCancel=logTimeout).addBoth(called)

    return d


# f() will be timed out if the random delay is greater than 3 seconds
task.react(main)
