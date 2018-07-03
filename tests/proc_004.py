#!/usr/bin/env python3

from taptaptap3.proc import plan, ok, out

plan(tests=10)
ok("Starting the program")
ok("Starting the engine")
ok("Find the object", skip="Setup required")
ok("Terminate", skip="Setup missing")

out()


##     validity: -1
## ok testcases: 4 / 10
##      bailout: no
##       stderr: program
##       stderr: engine
##       stderr: object
##       stderr: Terminate
##       stderr: SKIP
##       stderr: Setup required
##       stderr: Setup missing
