#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, out

plan(tests=1)
ok('Proving it right')
not_ok('and failing')

out()



##     validity: -1
## ok testcases: 1 / 2
##      bailout: no
##       stdout: failing
