#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap import TapTestcase
from taptaptap.exc import *

import io
import pickle
import unittest


class TestTapTestcase(unittest.TestCase):
    def testField(self):
        def assign(tc, what):
            tc.field = what

        tc = TapTestcase()
        self.assertIsNone(tc.field)
        tc.field = False
        self.assertFalse(tc.field)
        tc.field = True
        self.assertTrue(tc.field)
        tc.field = 'not ok'
        self.assertFalse(tc.field)
        tc.field = 'ok'
        self.assertTrue(tc.field)
        tc.field = 'not ok'
        self.assertFalse(tc.field)
        tc.field = None
        self.assertEquals(tc.field, None)

        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, 'nonsense')

    def testNumber(self):
        def assign(tc, what):
            tc.number = what

        tc = TapTestcase()
        self.assertIsNone(tc.number)
        tc.number = 0
        self.assertEquals(tc.number, 0)
        tc.number = 5
        self.assertEquals(tc.number, 5)
        tc.number = "8"
        self.assertEquals(tc.number, 8)
        tc.number = "9 "
        self.assertEquals(tc.number, 9)
        tc.number = None
        self.assertIsNone(tc.number)

        self.assertRaises(ValueError, assign, tc, -19)
        self.assertRaises(ValueError, assign, tc, "-20")
        self.assertRaises(ValueError, assign, tc, '0.75')
        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, 'nonsense')

    def testDescription(self):
        tc = TapTestcase()
        self.assertEquals(tc.description, "")

        tc.description = "Hello World"
        self.assertEquals(tc.description, "Hello World")

        tc.description = None
        self.assertEquals(tc.description, "")

    def testDirective(self):
        def assign(tc, what):
            tc.directive = what

        tc = TapTestcase()
        self.assertEquals(tc.directive, "")
        self.assertFalse(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = "skip hello world"
        self.assertIn('hello world', tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = "Skip the universe"
        self.assertIn('the universe', tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = "Todo hell world"
        self.assertTrue('hell world', tc.directive)
        self.assertFalse(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = "skip abc def TODO bcd efg todo cde fgh"
        self.assertIn('abc def', tc.directive)
        self.assertIn('bcd efg', tc.directive)
        self.assertIn('cde fgh', tc.directive)
        self.assertTrue(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = None
        self.assertEquals(tc.directive, "")
        self.assertFalse(tc.skip)
        self.assertFalse(tc.todo)

    def testData(self):
        tc = TapTestcase()
        tc.data = ["My name is Bond"]
        self.assertEquals(tc.data, ["My name is Bond"])

        tc.data += [", James Bond"]
        self.assertEquals(tc.data, ["My name is Bond", ", James Bond"])

        tc.data = [1, 2, 3]
        self.assertEquals(tc.data, [1, 2, 3])

        tc.data += [5]
        self.assertEquals(tc.data, [1, 2, 3, 5])

        tc.data = None
        self.assertEquals(tc.data, [])

    def testCopy(self):
        tc = TapTestcase()
        tc.description = "desc1"
        tc2 = tc.copy()

        self.assertEquals(tc.description, "desc1")
        self.assertEquals(tc2.description, "desc1")
        tc2.description = "desc2"
        self.assertEquals(tc.description, "desc1")
        self.assertEquals(tc2.description, "desc2")

        # mutables introduce undefined behavior
        data = ["The world", "is not enough"]
        tc = TapTestcase()
        tc.data = data
        tc2 = tc.copy()

        self.assertEquals(tc.data, data)
        self.assertEquals(tc2.data, data)
        tc2.data += ["!"]
        self.assertEquals(tc.data, ["The world", "is not enough", "!"])
        ## Undefined behavior = untested
        #self.assertEquals(tc.data, ["The world", "is not enough"])

    def testPickle(self):
        dump_file = io.StringIO()

        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = 'TODO homepage skip that'
        tc.description = "description"
        tc.data = ['The answer to', 'life', 'universe', 'everything']

        self.assertTrue(tc.todo and tc.skip)
        pickle.dump(tc, dump_file)
        dump_file.seek(0)

        tc = pickle.load(dump_file)
        self.assertFalse(tc.field)
        self.assertEquals(tc.number, 42)
        self.assertIn("homepage", tc.directive)
        self.assertIn("that", tc.directive)
        self.assertTrue(tc.todo and tc.skip)
        self.assertEquals(tc.description, "description")
        self.assertTrue(len(tc.data) == 4 and tc.data[1] == 'life')

    def testRepr(self):
        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = 'TODO 007 skip james bond'
        tc.description = "The world is not enough"
        tc.data = ['The answer to', 'life', 'universe', 'everything']

        text = unicode(tc)
        self.assertIn('not ok', text)
        self.assertIn('42', text)
        self.assertIn('007', text)
        self.assertIn('james bond', text)
        self.assertIn('The world is not enough', text)
        self.assertIn('universe', text)

if __name__ == '__main__':
    unittest.main()
