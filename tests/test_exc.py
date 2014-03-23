#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap import TapDocumentReader
from taptaptap.exc import *

import unittest


def parse(source, strict=False):
    TapDocumentReader().from_string(source, lenient=not strict)


class TestExceptions(unittest.TestCase):
    def testParseError(self):
        two_tcs1           = '1..1\nnot ok 1\nnot ok 1\n'
        no_plan            = 'not ok\n'
        no_integer_version = 'TAP version 13h\n1..1\nok\n'
        invalid_plan       = '1..1b\nok\n'
        invalid_testcase   = '1..1\nok 1c\n'
        negative_plan      = '1..0\n '

        self.assertRaises(TapInvalidNumbering, parse, two_tcs1)
        self.assertRaises(TapInvalidNumbering, parse, two_tcs1, True)

        self.assertRaises(TapMissingPlan, parse, no_plan)
        self.assertRaises(TapMissingPlan, parse, no_plan, True)

        parse(no_integer_version)
        self.assertRaises(TapParseError, parse, no_integer_version, True)

        self.assertRaises(TapMissingPlan, parse, invalid_plan)
        self.assertRaises(TapParseError, parse, invalid_plan, True)

        parse(invalid_testcase)
        self.assertRaises(TapParseError, parse, invalid_testcase)

        parse(negative_plan)
        self.assertRaises(TapParseError, parse, negative_plan, True)

    def testBailout(self):
        try:
            raise TapBailout("Message")
            self.assertTrue(False)
        except TapBailout as e:
            self.assertIn('Bail out!', str(e))

if __name__ == '__main__':
    unittest.main()
