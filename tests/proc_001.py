#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, out

plan(tests=2)
ok('Proving it right')
not_ok('and failing')

out()



##     validity: -1
## ok testcases: 1 / 2
##      bailout: no
##       stderr: failing
