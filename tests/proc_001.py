#!/usr/bin/env python3

from taptaptap3.proc import plan, ok, not_ok, out

plan(tests=2)
ok("Proving it right")
not_ok("and failing")

out()


##     validity: -1
## ok testcases: 1 / 2
##      bailout: no
##       stderr: failing
