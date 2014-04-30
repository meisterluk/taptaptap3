#!/usr/bin/env python

from taptaptap.proc import plan, ok, not_ok, write

plan(tests=10)
ok('Starting the program')
not_ok('Starting the engine')
not_ok('Find the object', skip='Setup required')
not_ok('Terminate', skip='Setup required')

write()
