#!/usr/bin/env python3

from taptaptap3.proc import plan, ok, not_ok, out

plan(first=1, last=13)
ok("Starting the program")
ok("Starting the engine")
ok("Find the object")
ok("Grab it", todo=True)
ok("Use it", todo=True)

2 * 2 == 4 and ok("2 * 2 == 4") or not_ok("2 * 2 != 4")

out()


##     validity: -1
## ok testcases: 6 / 13
##      bailout: no
##       stderr: 2 * 2 == 4
##       stderr: TODO
##       stderr: ~TRUE
##       stderr: ~True
##       stderr: ~true
