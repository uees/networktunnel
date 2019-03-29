from twisted.internet import defer


# A callback that unpacks and prints the results of a DeferredList
def printResult(result):
    for (success, value) in result:
        if success:
            print('Success:', value)
        else:
            print('Failure:', value.getErrorMessage())


# Create three deferreds.
deferred1 = defer.Deferred()
deferred2 = defer.Deferred()
deferred3 = defer.Deferred()

# 标准的 DeferredList 永远不会调用 errback，但是传递给 DeferredList 的延迟失败仍然会返回，除非 consumeErrors 被传递为 True
# Pack them into a DeferredList
dl = defer.DeferredList([deferred1, deferred2, deferred3], consumeErrors=True)

# Add our callback
dl.addCallback(printResult)

# Fire our three deferreds with various values.
deferred1.callback('one')
deferred2.errback(Exception('bang!'))
deferred3.callback('three')

# At this point, dl will fire its callback, printing:
#    Success: one
#    Failure: bang!
#    Success: three
# (note that defer.SUCCESS == True, and defer.FAILURE == False)


# 如果在将 Deferred 添加到 DeferredList 之后向 Deferred 添加回调，那么这个回调返回的值将不会被赋予 DeferredList 的回调。
# 为了避免混淆，我们建议在 DeferredList 中使用 Deferred 后不要向其添加回调。

def printResult(result):
    print(result)


def addTen(result):
    return result + " ten"


# Deferred gets callback before DeferredList is created
deferred1 = defer.Deferred()
deferred2 = defer.Deferred()
deferred1.addCallback(addTen)
dl = defer.DeferredList([deferred1, deferred2])
dl.addCallback(printResult)
deferred1.callback("one")  # fires addTen, checks DeferredList, stores "one ten"
deferred2.callback("two")
# At this point, dl will fire its callback, printing:
#     [(1, 'one ten'), (1, 'two')]

# Deferred gets callback after DeferredList is created
deferred1 = defer.Deferred()
deferred2 = defer.Deferred()
dl = defer.DeferredList([deferred1, deferred2])
deferred1.addCallback(addTen)  # will run *after* DeferredList gets its value
dl.addCallback(printResult)
deferred1.callback("one")  # checks DeferredList, stores "one", fires addTen
deferred2.callback("two")
# At this point, dl will fire its callback, printing:
#     [(1, 'one), (1, 'two')]
