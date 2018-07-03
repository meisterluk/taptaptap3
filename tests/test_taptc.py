#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from taptaptap3 import TapTestcase, YamlData
from taptaptap3 import TapActualNumbering, TapNumbering
from taptaptap3.exc import TapInvalidNumbering

import io
import pickle
import unittest


class TestTapYaml(unittest.TestCase):

    def testYamlData(self):
        d = YamlData([1, 2, 3])
        self.assertEqual(str(d), "---\n- 1\n- 2\n- 3\n...\n")


class TestTapTestcase(unittest.TestCase):

    def testEmpty(self):
        tc = TapTestcase()
        self.assertIsNone(tc.field)
        self.assertIsNone(tc.number)
        self.assertEqual(tc.description, "")
        self.assertEqual(tc.directive, "")
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
        tc.field = "not ok"
        self.assertFalse(tc.field)
        tc.field = "ok"
        self.assertTrue(tc.field)
        tc.field = "not ok"
        self.assertFalse(tc.field)
        tc.field = None
        self.assertIsNone(tc.field)

        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, "nonsense")

    def testNumber(self):

        def assign(tc, what):
            tc.number = what

        tc = TapTestcase()
        tc.number = 0
        self.assertEqual(tc.number, 0)
        tc.number = 5
        self.assertEqual(tc.number, 5)
        tc.number = "8"
        self.assertEqual(tc.number, 8)
        tc.number = "9 "
        self.assertEqual(tc.number, 9)
        tc.number = None
        self.assertIsNone(tc.number)

        self.assertRaises(ValueError, assign, tc, -19)
        self.assertRaises(ValueError, assign, tc, "-20")
        self.assertRaises(ValueError, assign, tc, "0.75")
        self.assertRaises(ValueError, assign, tc, object())
        self.assertRaises(ValueError, assign, tc, "nonsense")

    def testDescription(self):
        tc = TapTestcase()
        tc.description = "Hello World"
        self.assertEqual(tc.description, "Hello World")

    def testDirective(self):

        def assign(tc, what):
            tc.directive = what

        tc = TapTestcase()

        tc.directive = "skip hello world"
        self.assertIn("hello world", tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = "Skip the universe"
        self.assertIn("the universe", tc.directive)
        self.assertTrue(tc.skip)
        self.assertFalse(tc.todo)

        tc.directive = "Todo hell world"
        self.assertTrue("hell world", tc.directive)
        self.assertFalse(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = "skip abc def TODO bcd efg todo cde fgh"
        self.assertIn("abc def", tc.directive)
        self.assertIn("bcd efg", tc.directive)
        self.assertIn("cde fgh", tc.directive)
        self.assertTrue(tc.skip)
        self.assertTrue(tc.todo)

        tc.directive = ""
        self.assertEqual(tc.directive, "")
        self.assertFalse(tc.skip)
        self.assertFalse(tc.todo)

    def testData(self):
        tc = TapTestcase()
        tc.data = ["My name is Bond"]
        self.assertEqual(tc.data, ["My name is Bond"])

        tc.data += [", James Bond"]
        self.assertEqual(tc.data, ["My name is Bond", ", James Bond"])

        tc.data = [1, 2, 3]
        self.assertEqual(tc.data, [1, 2, 3])

        tc.data += [5]
        self.assertEqual(tc.data, [1, 2, 3, 5])

        tc.data = []
        self.assertEqual(tc.data, [])

    def testCopy(self):
        tc = TapTestcase()
        tc.description = "desc1"
        tc2 = tc.copy()

        self.assertEqual(tc.description, "desc1")
        self.assertEqual(tc2.description, "desc1")
        tc2.description = "desc2"
        self.assertEqual(tc.description, "desc1")
        self.assertEqual(tc2.description, "desc2")

        tc.description = "desc3"
        self.assertEqual(tc.description, "desc3")
        self.assertEqual(tc2.description, "desc2")

    def testImmutability(self):
        # mutables introduce undefined behavior
        data = ["The world", "is not enough"]
        tc = TapTestcase()
        tc.data = data
        tc2 = tc.copy()

        self.assertEqual(tc.data, data)
        self.assertEqual(tc2.data, data)
        tc2.data += ["!"]
        self.assertEqual(tc2.data, ["The world", "is not enough", "!"])
        self.assertEqual(tc.data, ["The world", "is not enough"])

    def testPickle(self):
        dump_file = io.BytesIO()

        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = "TODO homepage skip that"
        tc.description = "description"
        tc.data = ["The answer to", "life", "universe", "everything"]

        self.assertTrue(tc.todo and tc.skip)
        pickle.dump(tc, dump_file)
        dump_file.seek(0)

        tc = pickle.load(dump_file)
        self.assertFalse(tc.field)
        self.assertEqual(tc.number, 42)
        self.assertIn("homepage", tc.directive)
        self.assertIn("that", tc.directive)
        self.assertTrue(tc.todo and tc.skip)
        self.assertEqual(tc.description, "description")
        self.assertTrue(len(tc.data) == 4 and tc.data[1] == "life")

    def testStringRepr(self):
        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = "TODO 007 skip james bond"
        tc.description = "The world is not enough"
        tc.data = ["The answer to", "life", "universe", "everything"]

        text = str(tc)
        self.assertIn("not ok", text)
        self.assertIn("42", text)
        self.assertIn("007", text)
        self.assertIn("james bond", text)
        self.assertIn("The world is not enough", text)
        self.assertIn("universe", text)

    def testExactStringRepr(self):
        tc = TapTestcase()
        tc.field = False
        tc.number = 42
        tc.directive = "TODO open for discussion SKIP work in progress"
        tc.description = 'Test "string representation" of ümläuts'
        tc.data = [YamlData(["item 1", "item 2", "item 3"])]

        self.assertEqual(
            'not ok 42 - Test "string representation" '
            "of ümläuts  # SKIP work in progress TODO open for discussion\n"
            "---\n- item 1\n- item 2\n- item 3\n...\n",
            str(tc),
        )


class TestTapNumbering(unittest.TestCase):

    def testConstructor(self):
        num = TapNumbering(first=1, last=1)
        self.assertEqual(len(num), 1)
        self.assertNotIn(0, num)
        self.assertIn(1, num)
        self.assertNotIn(2, num)

        num = TapNumbering(first=1, last=0)
        self.assertEqual(len(num), 0)
        self.assertNotIn(0, num)
        self.assertNotIn(1, num)
        self.assertNotIn(2, num)

        num = TapNumbering(first=1, last=3)
        self.assertEqual(len(num), 3)
        self.assertIn(1, num)
        self.assertIn(2, num)
        self.assertIn(3, num)
        self.assertNotIn(4, num)

        num = TapNumbering(tests=3)
        self.assertEqual(len(num), 3)
        self.assertNotIn(-3, num)
        self.assertNotIn(0, num)
        self.assertIn(1, num)
        self.assertIn(2, num)
        self.assertIn(3, num)
        self.assertNotIn(4, num)

        num = TapNumbering(first=42, last=567)
        self.assertEqual(len(num), 526)
        self.assertNotIn(4, num)
        self.assertNotIn(41, num)
        self.assertIn(42, num)
        self.assertIn(106, num)
        self.assertIn(526, num)
        self.assertNotIn(568, num)

        num = TapNumbering(first=5, last=3, lenient=True)
        self.assertEqual(len(num), 0)

        self.assertTrue(bool(num))
        self.assertRaises(ValueError, TapNumbering, first=1, last=3, tests=2)
        self.assertRaises(ValueError, TapNumbering, first=None, last=None, tests=None)
        self.assertRaises(
            TapInvalidNumbering, TapNumbering, first=5, last=3, lenient=False
        )

    def testEnumeration(self):
        num = TapNumbering(tests=5)
        self.assertEqual(num.enumeration(), [1, 2, 3, 4, 5])

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
        self.assertEqual(num.normalized_plan(), "1..9")
        self.assertEqual(num.range(), (5, 13))
        num.inc()
        self.assertEqual(num.normalized_plan(), "1..10")
        self.assertEqual(num.range(), (5, 14))

        num = TapNumbering(tests=0)
        self.assertEqual(num.normalized_plan(), "1..0")
        self.assertEqual(num.range(), (1, 0))

    def testPickle(self):
        dump_file = io.BytesIO()

        num = TapNumbering(tests=16)
        pickle.dump(num, dump_file)
        dump_file.seek(0)

        num = pickle.load(dump_file)
        self.assertEqual(num.range(), (1, 16))

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


if __name__ == "__main__":
    unittest.main()
