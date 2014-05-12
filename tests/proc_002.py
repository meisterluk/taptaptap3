#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, out

plan(first=1, last=3)
ok('Starting the program')
ok('Starting the engine')
ok('Find the object')

out()



##     validity: 0
## ok testcases: 3 / 3
##      bailout: no
##       stdout: program
