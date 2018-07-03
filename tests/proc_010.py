#!/usr/bin/env python3

from taptaptap3.proc import plan, ok, out, bailout

plan(first=1, last=2)
ok("before")
bailout("now")
ok("after")

out()


##     validity: -2
## ok testcases: 2 / 2
##      bailout: yes
##       stderr: before
##       stderr: Bail out! now
##       stderr: after
