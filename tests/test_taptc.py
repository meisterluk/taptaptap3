#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from taptaptap import TapTestcase, YamlData, TapActualNumbering, TapInvalidNumbering, TapNumbering
from taptaptap.exc import *

import io
import pickle
import unittest


class TestTapYaml(unittest.TestCase):
    def testYamlData(self):
        d = YamlData([1, 2, 3])
        self.assertEquals(unicode(d), u'---\n- 1\n- 2\n- 3\n...\n')


class TestTapTestcase(unittest.TestCase):
    def testEmpty(self):
        tc = TapTestcase()
        self.assertIsNone(tc.field)
        self.assertIsNone(tc.number)
        self.assertEquals(tc.description, '')
        self.assertEquals(tc.directive, "")
        self.assertFalse(tc.skip)
        self.assertFalse(tc.todo)

    def testField(self):
        def assign(tc, what):
            tc.field = what

        tc = TapTestcase()
        tc.field = False
        self.assertFalse(tc.field)
        tc.field = True
        self.assertTrue(tc.field)
        tc.field = u'not ok'
        self.assertFalse(tc.field)
        tc.field = u'ok'
        self.assertTrue(tc.field)
        tc.field = u'not ok'
        self.assertFalse(tc.field)
        tc.field = None
        self.assertIsNone(tc.field)

        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, u'nonsense')

    def testNumber(self):
        def assign(tc, what):
            tc.number = what

        tc = TapTestcase()
        tc.number = 0
        self.assertEquals(tc.number, 0)
        tc.number = 5
        self.assertEquals(tc.number, 5)
        tc.number = u'8'
        self.assertEquals(tc.number, 8)
        tc.number = u'9 '
        self.assertEquals(tc.number, 9)
        tc.number = None
        self.assertIsNone(tc.number)

        self.assertRaises(ValueError, assign, tc, -19)
        self.assertRaises(ValueError, assign, tc, u'-20')
        self.assertRaises(ValueError, assign, tc, u'0.75')
        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, u'nonsense')

    def testDescription(self):
        tc = TapTestcase()
        tc.description = u'Hello World'
        self.assertEquals(tc.description, u'Hello World')

    def testDirective(self):
        def assign(tc, what):
            tc.directive = what

        tc = TapTestcase()

        tc.directive = u'skip hello world'
        self.assertIn(u'hello world', tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = u'Skip the universe'
        self.assertIn(u'the universe', tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = u'Todo hell world'
        self.assertTrue(u'hell world', tc.directive)
        self.assertFalse(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = u'skip abc def TODO bcd efg todo cde fgh'
        self.assertIn(u'abc def', tc.directive)
        self.assertIn(u'bcd efg', tc.directive)
        self.assertIn(u'cde fgh', tc.directive)
        self.assertTrue(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = u''
        self.assertEquals(tc.directive, u'')
        self.assertFalse(tc.skip)
        self.assertFalse(tc.todo)

    def testData(self):
        tc = TapTestcase()
        tc.data = [u'My name is Bond']
        self.assertEquals(tc.data, [u'My name is Bond'])

        tc.data += [u', James Bond']
        self.assertEquals(tc.data, [u'My name is Bond', u', James Bond'])

        tc.data = [1, 2, 3]
        self.assertEquals(tc.data, [1, 2, 3])

        tc.data += [5]
        self.assertEquals(tc.data, [1, 2, 3, 5])

        tc.data = []
        self.assertEquals(tc.data, [])

    def testCopy(self):
        tc = TapTestcase()
        tc.description = u'desc1'
        tc2 = tc.copy()

        self.assertEquals(tc.description, u'desc1')
        self.assertEquals(tc2.description, u'desc1')
        tc2.description = u'desc2'
        self.assertEquals(tc.description, u'desc1')
        self.assertEquals(tc2.description, u'desc2')

        tc.description = u'desc3'
        self.assertEquals(tc.description, u'desc3')
        self.assertEquals(tc2.description, u'desc2')

    def testImmutability(self):
        # mutables introduce undefined behavior
        data = [u'The world', u'is not enough']
        tc = TapTestcase()
        tc.data = data
        tc2 = tc.copy()

        self.assertEquals(tc.data, data)
        self.assertEquals(tc2.data, data)
        tc2.data += [u'!']
        self.assertEquals(tc2.data, [u'The world', u'is not enough', u'!'])
        self.assertEquals(tc.data, [u'The world', u'is not enough'])

    def testPickle(self):
        dump_file = io.BytesIO()

        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = u'TODO homepage skip that'
        tc.description = u'description'
        tc.data = [u'The answer to', u'life', u'universe', u'everything']

        self.assertTrue(tc.todo and tc.skip)
        pickle.dump(tc, dump_file)
        dump_file.seek(0)

        tc = pickle.load(dump_file)
        self.assertFalse(tc.field)
        self.assertEquals(tc.number, 42)
        self.assertIn(u'homepage', tc.directive)
        self.assertIn(u'that', tc.directive)
        self.assertTrue(tc.todo and tc.skip)
        self.assertEquals(tc.description, u'description')
        self.assertTrue(len(tc.data) == 4 and tc.data[1] == u'life')

    def testStringRepr(self):
        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = u'TODO 007 skip james bond'
        tc.description = u"The world is not enough"
        tc.data = [u'The answer to', u'life', u'universe', u'everything']

        text = unicode(tc)
        self.assertIn(u'not ok', text)
        self.assertIn(u'42', text)
        self.assertIn(u'007', text)
        self.assertIn(u'james bond', text)
        self.assertIn(u'The world is not enough', text)
        self.assertIn(u'universe', text)

    def testExactStringRepr(self):
        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = u'TODO open for discussion SKIP work in progress'
        tc.description = u'Test "string representation" of ümläuts'
        tc.data = [YamlData([u'item 1', u'item 2', u'item 3'])]

        self.assertEquals(u'not ok 42 - Test "string representation" '
            u'of ümläuts # SKIP work in progress TODO open for discussion\n'
            u'  ---\n  - item 1\n  - item 2\n  - item 3\n  ...\n', unicode(tc))


class TestTapNumbering(unittest.TestCase):
    def testConstructor(self):
        num = TapNumbering(first=1, last=1)
        self.assertEquals(len(num), 1)
        self.assertNotIn(0, num)
        self.assertIn(1, num)
        self.assertNotIn(2, num)

        num = TapNumbering(first=1, last=0)
        self.assertEquals(len(num), 0)
        self.assertNotIn(0, num)
        self.assertNotIn(1, num)
        self.assertNotIn(2, num)

        num = TapNumbering(first=1, last=3)
        self.assertEquals(len(num), 3)
        self.assertIn(1, num)
        self.assertIn(2, num)
        self.assertIn(3, num)
        self.assertNotIn(4, num)

        num = TapNumbering(tests=3)
        self.assertEquals(len(num), 3)
        self.assertNotIn(-3, num)
        self.assertNotIn(0, num)
        self.assertIn(1, num)
        self.assertIn(2, num)
        self.assertIn(3, num)
        self.assertNotIn(4, num)

        num = TapNumbering(first=42, last=567)
        self.assertEquals(len(num), 526)
        self.assertNotIn(4, num)
        self.assertNotIn(41, num)
        self.assertIn(42, num)
        self.assertIn(106, num)
        self.assertIn(526, num)
        self.assertNotIn(568, num)

        num = TapNumbering(first=5, last=3, lenient=True)
        self.assertEquals(len(num), 0)

        self.assertTrue(bool(num))
        self.assertRaises(ValueError, TapNumbering, first=1, last=3, tests=2)
        self.assertRaises(ValueError, TapNumbering,
                          first=None, last=None, tests=None)
        self.assertRaises(TapInvalidNumbering, TapNumbering,
                          first=5, last=3, lenient=False)

    def testEnumeration(self):
        num = TapNumbering(tests=5)
        self.assertEquals(num.enumeration(), [1, 2, 3, 4, 5])

    def testInc(self):
        num = TapNumbering(tests=5)
        self.assertTrue(4 in num)
        self.assertTrue(5 in num)
        self.assertFalse(6 in num)
        num.inc()
        self.assertTrue(5 in num)
        self.assertTrue(6 in num)
        self.assertFalse(7 in num)

    def testNormalizedRangeAndPlan(self):
        num = TapNumbering(first=5, last=13)
        self.assertEquals(num.normalized_plan(), '1..9')
        self.assertEquals(num.range(), (5, 13))
        num.inc()
        self.assertEquals(num.normalized_plan(), '1..10')
        self.assertEquals(num.range(), (5, 14))

        num = TapNumbering(tests=0)
        self.assertEquals(num.normalized_plan(), '1..0')
        self.assertEquals(num.range(), (1, 0))

    def testPickle(self):
        dump_file = io.BytesIO()

        num = TapNumbering(tests=16)
        pickle.dump(num, dump_file)
        dump_file.seek(0)

        num = pickle.load(dump_file)
        self.assertEquals(num.range(), (1, 16))

    def testIter(self):
        num = TapNumbering(first=4, last=10)
        iters = [4, 5, 6, 7, 8, 9, 10]
        for entry in num:
            iters.remove(entry)
        if iters:
            raise ValueError("Not all numbers iterated")
 

class TestTapActualNumbering(unittest.TestCase):
    def testEverything(self):
        num = TapActualNumbering([1, None, 3])
        self.assertIn(1, num)
        self.assertIn(3, num)


if __name__ == '__main__':
    unittest.main()
