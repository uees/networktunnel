# 将阻塞代码与Twisted集成在一起
# 在某种程度上，您可能需要调用阻塞函数:第三方库中的许多函数都有长时间运行的阻塞函数。
# 没有办法“强制”一个函数是异步的:它必须以这种特定的方式编写。
# 在这种情况下，Twisted提供了在单独的线程中运行阻塞代码的能力，而不是让它阻塞您的应用程序。
# ` twisted.internet.threads.deferToThread` 函数将设置一个线程来运行阻塞函数，返回一个 Deferred，然后在线程完成时触发该函数。


from twisted.internet import threads, reactor


def largeFibonnaciNumber():
    """
    Represent a long running blocking function by calculating
    the TARGETth Fibonnaci number
    """
    TARGET = 10000

    first = 0
    second = 1

    for i in range(TARGET - 1):
        new = first + second
        first = second
        second = new

    return second


def fibonacciCallback(result):
    """
    Callback which manages the largeFibonnaciNumber result by
    printing it out
    """
    print("largeFibonnaciNumber result =", result)
    # make sure the reactor stops after the callback chain finishes,
    # just so that this example terminates
    reactor.stop()


def run():
    """
    Run a series of operations, deferring the largeFibonnaciNumber
    operation to a thread and performing some other operations after
    adding the callback
    """
    # get our Deferred which will be called with the largeFibonnaciNumber result
    d = threads.deferToThread(largeFibonnaciNumber)  # 这个操作不会阻塞我们的主线程
    # add our callback to print it out
    d.addCallback(fibonacciCallback)
    print("1st line after the addition of the callback")
    print("2nd line after the addition of the callback")


if __name__ == '__main__':
    run()
    reactor.run()
