#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap import TapDocument, TapNumbering
from taptaptap.exc import *

import unittest


def parse(source, strict=False):
    TapDocumentReader().from_string(source, lenient=not strict)

class TestTapNumbering(unittest.TestCase):
    def testConstructorAndLength(self):
        # Use start & end (and strict)
        obj = TapNumbering(first=1, last=1, strict=False)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 1)

        obj = TapNumbering(first=1, last=0, strict=False)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        obj = TapNumbering(first=1, last=0) # strict is False per default
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        self.assertRaises(TapInvalidNumbering,
            lambda: TapNumbering(first=1, last=0, strict=True))

        obj = TapNumbering(first=5, last=12)
        self.assertEquals(obj.first, 5)
        self.assertEquals(len(obj), 8)

        self.assertRaises(ValueError,
            lambda: TapNumbering(first=None, last=None, tests=None))

        # Use tests
        obj = TapNumbering(tests=10)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 10)

        obj = TapNumbering(tests=0)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        obj = TapNumbering(tests=256.8, strict=False)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 256)

    def testContains(self):
        def valuetest(obj, intrange):
            for i in xrange(*intrange):
                self.assertIn(i, obj)
            self.assertNotIn(intrange[0] - 200, obj)
            self.assertNotIn(intrange[0] - 2, obj)
            self.assertNotIn(intrange[0] - 1, obj)
            self.assertNotIn(intrange[1] + 1, obj)
            self.assertNotIn(intrange[1] + 2, obj)
            self.assertNotIn(intrange[1] + 3, obj)
            self.assertNotIn(intrange[1] + 6, obj)
            self.assertNotIn(intrange[1] + 10, obj)
            self.assertNotIn(intrange[1] + 256, obj)

        zero = TapNumbering(tests=0)
        one = TapNumbering(tests=1)
        twenty = TapNumbering(tests=20)
        one_to_10 = TapNumbering(first=1, last=10)
        one_to_one = TapNumbering(first=1, last=1)
        one_to_zero = TapNumbering(first=1, last=0)
        five_to_10 = TapNumbering(first=5, last=10)
        five_to_five = TapNumbering(first=5, last=5)
        five_to_three = TapNumbering(first=5, last=3)

        self.assertFalse(0 in zero)
        self.assertFalse(-2 in zero)
        self.assertFalse(10 in zero)

        self.assertFalse(-25 in one)
        self.assertFalse(0 in one)
        self.assertTrue(1 in one)
        self.assertFalse(2 in one)
        self.assertFalse(42 in one)

        valuetest(twenty, [1, 21])
        valuetest(one_to_10, [1, 11])
        valuetest(one_to_one, [1, 2])
        valuetest(five_to_10, [5, 11])
        valuetest(five_to_five, [5, 6])

        self.assertFalse(-2 in one_to_zero)
        self.assertFalse(0 in one_to_zero)
        self.assertFalse(1 in one_to_zero)
        self.assertFalse(2 in one_to_zero)

        self.assertFalse(1 in five_to_three)
        self.assertFalse(3 in five_to_three)
        self.assertFalse(4 in five_to_three)
        self.assertFalse(5 in five_to_three)
        self.assertFalse(6 in five_to_three)

    def testParse(self):
        plan_zero = "0..0"
        plan_one = "1..1"
        plan_two = "1..2\n"
        plan_start_two = "2..3\n "
        plan_multichar = "20..999\n"

        plan_more = "1..6\nnot allowed text"
        plan_too_short = "1.."
        plan_invalid_start = " 1..1"
        plan_space = "3.. 6"
        plan_negative = "-1..1"
        plan_strict_test = "1..0"

        self.assertEquals(len(TapNumbering.parse(plan_zero)), 1)
        self.assertEquals(len(TapNumbering.parse(plan_one)), 1)
        self.assertEquals(len(TapNumbering.parse(plan_two)), 2)
        self.assertEquals(len(TapNumbering.parse(plan_start_two)), 2)
        self.assertEquals(len(TapNumbering.parse(plan_multichar)), 980)
        self.assertEquals(len(TapNumbering.parse(plan_strict_test)), 0)

        self.assertRaises(ValueError, lambda: TapNumbering.parse(plan_more))
        self.assertRaises(ValueError, lambda: TapNumbering.parse(plan_too_short))
        self.assertRaises(ValueError, lambda: TapNumbering.parse(plan_invalid_start))
        self.assertRaises(ValueError, lambda: TapNumbering.parse(plan_space))
        self.assertRaises(ValueError, lambda: TapNumbering.parse(plan_negative))
        self.assertRaises(TapInvalidNumbering,
            lambda: TapNumbering.parse(plan_strict_test, strict=True))

    def testInc(self):
        obj = TapNumbering(first=2, last=0)
        obj.inc()
        self.assertEquals(obj.first, 2)
        self.assertEquals(len(obj), 1)

        obj = TapNumbering(first=25, last=0)
        obj.inc()
        obj.inc()
        obj.inc()
        self.assertEquals(obj.first, 25)
        self.assertEquals(len(obj), 3)

        obj = TapNumbering(first=5, last=10)
        obj.inc()
        obj.inc()
        self.assertEquals(obj.first, 5)
        self.assertEquals(len(obj), 8)

    def testPlan(self):
        def expect(str_in, norm_out, uni_out):
            obj = TapNumbering.parse(str_in)
            self.assertEquals(obj.normalized_plan(), norm_out)
            self.assertEquals(unicode(obj), uni_out)

        def expect_invalid(str_in):
            obj = TapNumbering.parse(str_in)
            self.assertRaises(ValueError, obj.normalized_plan)
            self.assertRaises(ValueError, unicode, obj)

        expect('1..1', '1..1', '1..1')
        expect('1..1\n', '1..1', '1..1')
        expect('2..15 ', '1..14', '2..15')
        expect('99..100', '1..2', '99..100')
        expect('0..5', '1..6', '0..5')

        expect_invalid('1..0')
        expect_invalid('5..4')

    def testIter(self):
        def expect(str_spec, expect_values):
            iterations = 0
            for i in TapNumbering.parse(str_spec):
                self.assertTrue(iterations < len(expect_values))
                self.assertEquals(expect_values[iterations], i)
                iterations += 1

        expect('1..1', [1])
        expect('1..2', [1, 2])
        expect('3..3', [3])
        expect('42..100', range(42, 101))
        expect('0..1', [0, 1])
        expect('0..42', range(0, 43))

class TestTapDocument(unittest.TestCase):
    def testEmptyDocument(self):
        doc = TapDocument()
        self.assertRaises(ValueError, unicode, doc)

# TODO: Test TapDocument

if __name__ == '__main__':
    unittest.main()
