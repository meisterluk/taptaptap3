#!/usr/bin/env python

from taptaptap.proc import plan, ok, out

plan(tests=10)
ok('Starting the program')
ok('Starting the engine')
ok('Find the object')
ok('Transport object to target')
ok('Check for existing fire')
ok('Place it beneath the desk')
ok('Search for fire extinguisher')
ok('Extinguish fire')
ok('Put fire extinguisher back')
ok('Terminate')

out()



##     validity: 0
## ok testcases: 10 / 10
##      bailout: no
##       stdout: Find the object
