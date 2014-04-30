#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, write
from taptaptap.proc import get_doc

plan(tests=10)
ok('Starting the program')
ok('Starting the engine')
ok('Find the object')
ok('Still some steps missing', todo=True)

2 * 2 == 4 and ok('2 * 2 == 4') or not_ok('2 * 2 != 4')

assert not get_doc().bailed()

write()
