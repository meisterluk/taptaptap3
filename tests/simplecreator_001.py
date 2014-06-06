import taptaptap

@taptaptap.SimpleTapCreator
def runTests():
    yield True
    yield True
    yield False

print runTests()

##     validity: -1
## ok testcases: 2 / 3
##      bailout: yes
##       stdout: 1..3
##       stdout: ok
##       stdout: not ok
