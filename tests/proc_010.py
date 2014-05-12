#!/usr/bin/env python

from taptaptap.proc import plan, ok, out, bailout

plan(first=1, last=2)
ok('before')
bailout('now')
ok('after')

out()




##     validity: -2
## ok testcases: 2 / 2
##      bailout: yes
##       stdout: before
##       stderr: Bail out! now
##       stdout: after
