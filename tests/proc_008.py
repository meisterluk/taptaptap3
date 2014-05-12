#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, write, out

plan(first=1, last=1, tapversion=13)
2 * 2 == 4 and ok('2 * 2 == 4') or not_ok('2 * 2 != 4')
write('arithmetics checked')

out()




##     validity: 0
## ok testcases: 1 / 1
##      bailout: no
##       stdout: 2 * 2 == 4
##       stdout: TAP version 13
##       stdout: arithmetics checked
