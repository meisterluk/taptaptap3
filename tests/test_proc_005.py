#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, write, bailout
from taptaptap.proc import get_doc

plan(start=1, end=1)
ok('2 * 2 == 4')
bailout()

assert not get_doc().valid()  # must not be valid even though all testcases succeeded
assert get_doc().bailed()

write()
