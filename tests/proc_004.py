#!/usr/bin/env python

from taptaptap.proc import plan, ok, out

plan(tests=10)
ok('Starting the program')
ok('Starting the engine')
ok('Find the object', skip='Setup required')
ok('Terminate', skip='Setup missing')

out()



##     validity: -1
## ok testcases: 4 / 10
##      bailout: no
##       stdout: program
##       stdout: engine
##       stdout: object
##       stdout: Terminate
##       stdout: SKIP
##       stdout: Setup required
##       stdout: Setup missing
