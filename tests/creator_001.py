import taptaptap3


@taptaptap3.TapCreator
def runTests():
    yield {"ok": True, "description": "1 + 1 == 2"}
    yield {"ok": True, "description": "E = mc^2", "skip": "Still in discussion"}
    yield {"ok": False, "description": "2 + 2 = 5", "todo": "Fix surveillance state"}
    raise taptaptap3.exc.TapBailout("System failure!")


print(runTests())

##     validity: -2
## ok testcases: 2 / 3
##      bailout: yes
##       stdout: 1..3
##       stdout: 1 + 1
##       stdout: Fix surveillance
##       stdout: System failure!
