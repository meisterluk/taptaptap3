#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.path.append('../..')

from taptaptap import TapTestcase, YamlData, TapActualNumbering, TapNumbering
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
            u'of ümläuts # SKIP work in progress TODO open for discussion \n'
            u'  ---\n  - item 1\n  - item 2\n  - item 3\n  ...\n', unicode(tc))


class TestTapActualNumbering(unittest.TestCase):
    def testConstructorAndFirstLength(self):
        obj = TapActualNumbering((1, 0), [])
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        obj = TapActualNumbering((1, 1), [1])
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 1)

        obj = TapActualNumbering((42, 50), [])
        self.assertEquals(obj.first, 42)
        self.assertEquals(len(obj), 9)

        obj = TapActualNumbering((42, 50), range(42, 51))
        self.assertEquals(obj.first, 42)
        self.assertEquals(len(obj), 9)

        obj = TapActualNumbering((42, 50), range(42, 52))
        self.assertEquals(obj.first, 42)
        self.assertEquals(len(obj), 9)

    def testInitRange(self):
        obj = TapActualNumbering().init_range(first=1, last=1, strict=False)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 1)

        obj = TapActualNumbering().init_range(first=1, last=0, strict=False)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        # strict is False per default
        obj = TapActualNumbering().init_range(first=4, last=3)
        self.assertEquals(obj.first, 4)
        self.assertEquals(len(obj), 0)

        self.assertRaises(TapInvalidNumbering, lambda:
            TapActualNumbering().init_range(first=4, last=3, strict=True))

        obj = TapActualNumbering().init_range(first=5, last=12)
        self.assertEquals(obj.first, 5)
        self.assertEquals(len(obj), 8)

        self.assertRaises(ValueError, lambda: TapActualNumbering() \
            .init_range(first=None, last=None, tests=None))

        # Use tests
        obj = TapActualNumbering().init_range(tests=10)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 10)

        obj = TapActualNumbering().init_range(tests=0)
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 0)

        obj = TapActualNumbering().init_range(tests=256.8, strict=False)
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

        zero = TapActualNumbering((1, 0), [])
        one = TapActualNumbering((1, 1), [1])
        twenty = TapActualNumbering((1, 20), range(20))
        one_to_10 = TapActualNumbering((1, 10), range(10))
        one_to_one = TapActualNumbering((1, 1), [1])
        one_to_zero = TapActualNumbering((1, 0), [])
        five_to_10 = TapActualNumbering((5, 10), range(5, 11))
        five_to_five = TapActualNumbering((5, 5), [5])
        five_to_three = TapActualNumbering((5, 3), [3])

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

    def testGetEnumeration(self):
        obj = TapActualNumbering((1, 0), [])
        self.assertEquals(obj.get_enumeration(), [])

        obj = TapActualNumbering((1, 1), [1])
        self.assertEquals(obj.get_enumeration(), [1])

        obj = TapActualNumbering((1, 2), [1, 2])
        self.assertEquals(obj.get_enumeration(), [1, 2])

        obj = TapActualNumbering((1, 1), [None])
        self.assertEquals(obj.get_enumeration(), [1])

        obj = TapActualNumbering((1, 2), [None, None])
        self.assertEquals(obj.get_enumeration(), [1, 2])

        obj = TapActualNumbering((5, 7), [5, 6, 7])
        self.assertEquals(obj.get_enumeration(), [5, 6, 7])

        obj = TapActualNumbering((5, 7), [5, 7, None])
        self.assertEquals(obj.get_enumeration(True), [5, 7, 6])

        # error cases

        obj = TapActualNumbering((5, 5), [5, 5])
        self.assertRaises(IndexError, lambda: obj.get_enumeration())

        obj = TapActualNumbering((5, 18), [5, 6, 7, 8, 6])
        self.assertRaises(IndexError, lambda: obj.get_enumeration())


    def testInc(self):
        obj = TapActualNumbering((1, 0), [])
        obj.inc()
        self.assertEquals(obj.first, 1)
        self.assertEquals(len(obj), 1)

        obj = TapActualNumbering((25, 25), [25])
        obj.inc()
        obj.inc()
        obj.inc()
        self.assertEquals(obj.first, 25)
        self.assertEquals(len(obj), 4)

        obj = TapActualNumbering((5, 10), [5, 6, 7, 8, 9, 10])
        obj.inc()
        obj.inc()
        self.assertEquals(obj.first, 5)
        self.assertEquals(len(obj), 8)

    def testRange(self):
        obj = TapActualNumbering((1, 0), [])
        self.assertEquals(obj.range(), (1, 0))
        self.assertEquals(unicode(obj), u'1..0')

        obj = TapActualNumbering((1, 2), [1, 2])
        self.assertEquals(obj.range(), (1, 2))
        self.assertEquals(unicode(obj), u'1..2')

        obj = TapActualNumbering((256, 1024), range(256, 1025))
        self.assertEquals(obj.range(), (256, 1024))
        self.assertEquals(unicode(obj), u'256..1024')

    def testIter(self):
        def expect(num_range, expected_iterations):
            obj = TapActualNumbering(num_range, [])
            for num, i in enumerate(obj):
                self.assertEquals(i, expected_iterations[num])

        expect((1, 0), [])
        expect((1, 1), [1])
        expect((1, 2), [1, 2])
        expect((1, 10), range(1, 11))
        expect((42, 50), range(42, 51))

    def testMatches(self):
        obj = TapActualNumbering((1, 0), [])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((1, 1), [1])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((1, 1), [2])
        self.assertEquals(obj.matches(), False)

        obj = TapActualNumbering((1, 3), [1, 2, 3])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((1, 3), [1, None, 3])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((1, 3), [None, None, None])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((1, 3), [None, None, None, None])
        self.assertEquals(obj.matches(), False)

        obj = TapActualNumbering((6, 10), [6, 7, 8, 9, 10])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((6, 10), [6, 7, 8, 9, None])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((6, 10), [6, 7, 8, 9, 7])
        self.assertEquals(obj.matches(), False)

        obj = TapActualNumbering((6, 8), [6, None, 7])
        self.assertEquals(obj.matches(), True)

        obj = TapActualNumbering((6, 9), [6, None, 7])
        self.assertEquals(obj.matches(), False)


if __name__ == '__main__':
    unittest.main()
