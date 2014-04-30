#!/usr/bin/env python

"""Testcases for CLI tools"""

import sys
sys.path.append('../..')

import unittest
import subprocess
import taptaptap

combine_001002, combine_003010 = None, None

def init():
    global combine_001002, combine_003010
    with open('../examples/014.tap') as fp:
        combine_001002 = fp.read()
    with open('../examples/015.tap') as fp:
        combine_003010 = fp.read()

def validate(inputfile):
    cmd = ['tapvalidate', inputfile]
    proc = subprocess.Popen(cmd)
    proc.wait()
    return proc.returncode

def merge(inputfile1, inputfile2):
    cmd = ['tapmerge', inputfile1, inputfile2]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = proc.communicate()
    return out + err

class CLITests(unittest.TestCase):
    def testValidate(self):
        self.assertEquals(validate('examples/001.tap'), 1) # not ok
        self.assertEquals(validate('examples/002.tap'), 1) # missing TCs
        self.assertEquals(validate('examples/003.tap'), 0) # ok
        self.assertEquals(validate('examples/004.tap'), 1) # not ok
        self.assertEquals(validate('examples/005.tap'), 2) # Bailout!
        self.assertEquals(validate('examples/006.tap'), 0) # ok
        self.assertEquals(validate('examples/007.tap'), 0) # skip
        self.assertEquals(validate('examples/008.tap'), 0) # not ok
        self.assertEquals(validate('examples/009.tap'), 0) # ok
        self.assertEquals(validate('examples/010.tap'), 0) # ok
        self.assertEquals(validate('examples/011.tap'), 0) # not ok

    def testMerge(self):
        self.assertEquals(merge('examples/001.tap', 'examples/002.tap'), combine_001002)
        self.assertEquals(merge('examples/003.tap', 'examples/010.tap'), combine_003010)
        

if __name__ == '__main__':
    init()
    unittest.main()
