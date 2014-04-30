#!/usr/bin/env python

"""Test the iterator over a document"""

import sys
sys.path.append('../..')

import os.path
import subprocess
import taptaptap


BAILOUT_TESTCASE = '''1..4
ok
ok
Bail out! Stopped iteration
not ok
not ok
'''


EXAMPLES = "../examples/"

doc1 = taptaptap.TapDocumentReader().from_file(os.path.join('003.tap', EXAMPLES))
doc2 = taptaptap.TapDocumentReader().from_string(BAILOUT_TESTCASE)

iterations = 0
for tc in doc1:
    assert tc.field
    iterations += 1

assert iterations == 6

iterations = 0
for tc in doc2:
    iterations += 1

assert iterations == 2
