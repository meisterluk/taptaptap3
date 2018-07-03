#!/usr/bin/env python3

from taptaptap3.proc import plan, not_ok, out

plan(tests=1, tapversion=12, skip="environment does not fit")
not_ok("TypeError")

out()


##     validity: 0
## ok testcases: 0 / 1
##      bailout: no
##       stderr: TypeError
##       stderr: TAP version 12
##       stderr: environment does
