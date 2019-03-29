#
#  Basic Callback Functions
#
#
# callback(result)
# 只能运行一次，继续调用会触发 `twisted.internet.defer.AlreadyCalledError`
#
# errback(failure)
# 只能运行一次，继续调用会触发 `twisted.internet.defer.AlreadyCalledError`
#

# 延迟不会神奇地使代码不阻塞。
# 延迟不是一个非阻塞的护身符:它们是异步函数用来将结果传递回调的信号, 但是使用它们并不保证您有一个异步函数。

import time

from twisted.internet import defer

TARGET = 10000


def largeFibonnaciNumber():
    # create a Deferred object to return:
    d = defer.Deferred()

    def fib(n):
        a, b = 0, 1
        for i in range(n - 1):
            a, b = b, a+b
            if i % 100 == 0:
                print("Progress: calculating the %dth Fibonnaci number" % i)

        return b

    d.addCallback(fib)

    # return the Deferred with the answer:
    return d


timeBefore = time.time()

# call the function and get our Deferred
d = largeFibonnaciNumber()

timeAfter = time.time()

print("Total time taken for largeFibonnaciNumber call: %0.3f seconds" %
      (timeAfter - timeBefore))

# add a callback to it to print the number


def printNumber(number):
    print("The %dth Fibonacci number is %d" % (TARGET, number))


print("Adding the callback now.")

d.addCallback(printNumber)

# calculate the ten thousandth Fibonnaci number
d.callback(TARGET)


#
# Returning Deferreds from synchronous functions
# 除了 maybeDeferred 还可以在同步函数上做这样的调用转为 defer
# defer.succeed(result)
# defer.fail(failure)
#

# 例如一个同步函数
def synchronousIsValidUser(user):
    '''
    Return true if user is a valid user, false otherwise
    '''
    return user in ["Alice", "Angus", "Agnes"]


# 可以转为如下
def immediateIsValidUser(user):
    '''
    Returns a Deferred resulting in true if user is a valid user, false
    otherwise
    '''

    result = user in ["Alice", "Angus", "Agnes"]

    # return a Deferred object already called back with the value of result
    return defer.succeed(result)
