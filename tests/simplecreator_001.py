import taptaptap3


@taptaptap3.SimpleTapCreator
def runTests():
    yield True
    yield True
    yield False


print((runTests()))

##     validity: -1
## ok testcases: 2 / 3
##      bailout: no
##       stdout: 1..3
##       stdout: ok
##       stdout: not ok
