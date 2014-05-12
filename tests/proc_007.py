#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, out

plan(tests=1, tapversion=12, skip='environment does not fit')
not_ok('TypeError')

out()



##     validity: 0
## ok testcases: 0 / 1
##      bailout: no
##       stdout: TypeError
##       stdout: TAP version 12
##       stdout: environment does
