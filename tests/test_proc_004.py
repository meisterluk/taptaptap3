#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap.proc import plan, ok, not_ok, write
from taptaptap.proc import get_doc

plan(start=1, end=1)
2 * 2 == 4 and ok('2 * 2 == 4') or not_ok('2 * 2 != 4')
write()

assert get_doc().valid()


# plan() dumps the existing document

plan(start=1, end=2)

not_ok('Sanity check')
ok('Check health')

assert not get_doc().valid()

write()

