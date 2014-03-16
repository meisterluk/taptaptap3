#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap.proc import plan, ok, not_ok, write
from taptaptap.proc import get_doc

plan(tests=10)
ok('Starting the program')
ok('Starting the engine')
ok('Find the object')
ok('Transport object to target')
ok('Check for existing fire')
ok('Place it beneath the desk')
ok('Search for fire extinguisher')
ok('Extinguish fire')
ok('Put fire extinguisher back')
ok('Terminate')

write()
