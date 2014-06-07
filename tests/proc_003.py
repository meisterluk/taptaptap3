#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, out

plan(tests=10)
ok('Starting the program')
not_ok('Starting the engine')
not_ok('Find the object')
not_ok('Terminate')

out()



##     validity: -1
## ok testcases: 1 / 10
##      bailout: no
##       stderr: program
##       stderr: engine
##       stderr: object
##       stderr: Terminate
