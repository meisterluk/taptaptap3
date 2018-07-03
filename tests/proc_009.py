#!/usr/bin/env python3

from taptaptap3.proc import plan, ok, not_ok, out, bailout

plan(first=1, last=4)
not_ok("1 + 1 == 5")
ok("1 + 2 == 3")
ok("2 + 4 == 6")
ok("4 + 8 == 12")
bailout()

out()


##     validity: -2
## ok testcases: 3 / 4
##      bailout: yes
##       stderr: 4 + 8
##       stderr: Bail out!
