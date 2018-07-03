#!/usr/bin/env python3

from taptaptap3 import TapDocument, TapTestcase, TapDocumentIterator
from taptaptap3 import TapDocumentFailedIterator, TapDocumentActualIterator
from taptaptap3.exc import TapBailout

import unittest


class TestTapDocument(unittest.TestCase):

    def testEmptyDocument(self):
        doc = TapDocument()
        doc.add_plan(1, 0)
        self.assertEqual(doc.version, 13)
        self.assertEqual(doc.skip, False)
        self.assertEqual(len(doc), 0)
        self.assertEqual(str(doc), "1..0\n")

    def testConstructor(self):
        doc = TapDocument(version=13)
        self.assertEqual(doc.version, 13)

        doc = TapDocument(skip=True)
        self.assertTrue(doc.skip)

        doc.add_plan(1, 1)
        doc.add_testcase(TapTestcase())
        self.assertIn("skip", str(doc).lower())

    def testSet(self):
        doc = TapDocument()

        doc.set_version(12)
        self.assertEqual(doc.version, 12)

        doc.set_skip("this test expired")
        self.assertTrue(doc.skip)
        doc.set_skip(False)
        self.assertFalse(doc.skip)

    def testAdd(self):
        doc = TapDocument()

        doc.add_plan(1, 5, "SKIP wip")
        self.assertIn("wip", str(doc))
        self.assertIn("1..5", str(doc))

        tc = TapTestcase()
        tc.field = True
        tc.number = 1
        tc.description = "TC #1"
        tc.data = [
            ">>> int('88t')",
            "Traceback (most recent call last):",
            '  File "<stdin>", line 1, in <module>',
            "ValueError: invalid literal for int() with base 10: '88t'",
            {"locals": ["int"]},
        ]

        doc.add_testcase(tc)
        self.assertIn("wip", str(doc))
        self.assertIn("1..5", str(doc))
        self.assertNotIn("...", str(doc))
        self.assertIn("88t", str(doc))
        self.assertIn("locals", str(doc))

        doc.add_bailout(TapBailout("Filesystem crashed"))
        self.assertIn("Bail out! Filesystem crashed", str(doc))

    def testAddHeaderLine(self):
        doc = TapDocument()
        doc.add_plan(1, 0)

        doc.add_version_line(12)
        self.assertEqual(doc.version, 12)

        doc.add_header_line("Hello World")
        doc.add_header_line("Embrace!")
        self.assertIn("Hello World", str(doc))
        self.assertIn("Embrace!", str(doc))

    def testLength(self):
        doc = TapDocument()
        doc.add_plan(3, 7)

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_bailout(TapBailout("FS problem"))

        self.assertEqual(len(doc), 5)
        self.assertEqual(doc.actual_length(), 2)

    def testRangeAndPlan(self):
        doc = TapDocument()

        self.assertEqual(doc.range(), (1, 0))
        self.assertEqual(doc.actual_range(), (1, 0))
        self.assertEqual(doc.plan(), "1..0")
        self.assertEqual(doc.actual_plan(), "1..0")

        doc.add_plan(3, 7)

        self.assertEqual(doc.range(), (3, 7))
        self.assertEqual(doc.actual_range(), (1, 0))
        self.assertEqual(doc.plan(), "3..7")
        self.assertEqual(doc.actual_plan(), "1..0")

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_bailout(TapBailout("FS problem"))

        self.assertEqual(doc.range(), (3, 7))
        self.assertEqual(doc.actual_range(), (3, 4))
        self.assertEqual(doc.plan(), "3..7")
        self.assertEqual(doc.actual_plan(), "3..4")

    def testIn(self):
        doc = TapDocument()
        doc.add_plan(1, 3)

        self.assertFalse(1 in doc)
        self.assertFalse(2 in doc)
        self.assertFalse(42 in doc)

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())

        self.assertTrue(1 in doc)
        self.assertTrue(2 in doc)
        self.assertFalse(3 in doc)

        tc = TapTestcase()
        tc.number = 3
        doc.add_testcase(tc)

        self.assertTrue(1 in doc)
        self.assertTrue(2 in doc)
        self.assertTrue(3 in doc)
        self.assertFalse(4 in doc)
        self.assertFalse(5 in doc)
        self.assertFalse(6 in doc)

    def testIndexing(self):
        doc = TapDocument()
        doc.add_plan(1, 10)

        tc1 = TapTestcase()
        tc1.number = 1
        tc1.field = True
        tc1.description = "First testcase"

        tc2 = TapTestcase()
        tc2.field = True
        tc2.description = "Second testcase"

        tc3 = TapTestcase()
        tc3.number = 4
        tc3.field = False
        tc3.description = "Fourth testcase"

        tc4 = TapTestcase()
        tc4.field = True
        tc4.description = "Third testcase"

        tc5 = TapTestcase()
        tc5.field = True
        tc5.description = "Fifth testcase"

        doc.add_testcase(tc1)
        doc.add_testcase(tc2)
        doc.add_testcase(tc3)
        doc.add_testcase(tc4)
        doc.add_bailout(TapBailout("raising bailout"))
        doc.add_testcase(tc5)

        self.assertEqual(doc[1], tc1)
        self.assertEqual(doc[2], tc2)
        self.assertEqual(doc[3], tc4)
        self.assertEqual(doc[4], tc3)
        self.assertEqual(doc[5], tc5)
        self.assertEqual(doc[6], None)
        self.assertEqual(doc[10], None)

        self.assertRaises(IndexError, lambda: doc[0])
        self.assertRaises(IndexError, lambda: doc[11])
        self.assertRaises(IndexError, lambda: doc[256])

    def testCount(self):
        doc = TapDocument()

        tc1 = TapTestcase()
        tc1.field = True
        tc1.todo = True
        doc.add_testcase(tc1)

        tc2 = TapTestcase()
        tc2.field = False
        tc2.todo = True
        doc.add_testcase(tc2)

        tc3 = TapTestcase()
        tc3.field = False
        tc3.todo = True
        tc3.skip = True
        doc.add_testcase(tc3)

        tc4 = TapTestcase()
        tc4.field = True
        doc.add_testcase(tc4)

        self.assertEqual(doc.count_not_ok(), 2)
        self.assertEqual(doc.count_todo(), 3)
        self.assertEqual(doc.count_skip(), 1)

    def testBailout(self):
        doc = TapDocument()
        self.assertFalse(doc.bailed())

        doc.add_testcase(TapTestcase())
        self.assertFalse(doc.bailed())

        doc.add_bailout(TapBailout("FS crash"))
        self.assertTrue(doc.bailed())

        doc.add_bailout(TapBailout("Another crash"))
        self.assertTrue(doc.bailed())

        self.assertEqual(doc.bailout_message(), "FS crash")

    def testValid(self):
        # valid iff
        #   no bailout was thrown AND
        #   document itself is skipped OR
        #   all TCs exist AND
        #     are 'ok' OR
        #     skipped

        # default
        doc = TapDocument()
        doc.add_plan(1, 0)
        self.assertTrue(doc.valid())

        # bailout
        # must work without a plan
        doc.set_skip("Hello World")
        doc.add_bailout(TapBailout("filesystem problem"))
        self.assertFalse(doc.valid())

        # skipped
        doc = TapDocument()
        tc = TapTestcase()
        tc.field = False
        doc.add_testcase(tc)
        doc.add_plan(1, 1)
        doc.set_skip(True)
        self.assertTrue(doc.valid())

        # all tcs are ok
        doc = TapDocument()
        doc.add_testcase(TapTestcase(field=True))
        doc.add_testcase(TapTestcase(field=True))
        doc.add_testcase(TapTestcase(field=True))
        doc.add_testcase(TapTestcase(field=True))
        doc.add_plan(1, 4)
        self.assertTrue(doc.valid())

        # all tcs are ok
        doc = TapDocument()
        true_tc = TapTestcase()
        true_tc.field = True
        false_tc = TapTestcase()
        false_tc.field = False
        doc.add_testcase(true_tc)
        doc.add_testcase(true_tc)
        doc.add_testcase(true_tc)
        doc.add_testcase(false_tc)
        doc.add_plan(1, 4)
        self.assertFalse(doc.valid())

        # all tcs are skipped
        tc = TapTestcase()
        tc.field = False
        tc.skip = "Only testable in enterprise environment"
        doc = TapDocument()
        doc.set_skip(False)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_plan(1, 5)
        self.assertTrue(doc.valid())

        doc.add_bailout(TapBailout("System crashed"))
        self.assertFalse(doc.valid())


class TestTapDocumentIterator(unittest.TestCase):

    def testIterWithoutBailout(self):
        description = ["a", "b", "c", "d"]
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)
        for d in range(4):
            tc.description = description[d]  # use immutability property
            doc.add_testcase(tc)

        iterations = 0
        for d, tc in enumerate(iter(doc)):
            if d < 4:
                self.assertEqual(tc.description, description[d])
            else:
                self.assertIsNone(tc)
            iterations += 1

        for d, tc in enumerate(TapDocumentIterator(doc)):
            if d < 4:
                self.assertEqual(tc.description, description[d])
            else:
                self.assertIsNone(tc)
            iterations += 1

        self.assertEqual(iterations, 40)

    def testIter(self):
        description = ["a", "b", "c", "d"]
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)
        for d in range(4):
            tc.description = description[d]  # use immutability property
            doc.add_testcase(tc)
            if d == 2:
                doc.add_bailout(TapBailout("failure"))

        iterations = 0
        try:
            for d, tc in enumerate(iter(doc)):
                self.assertEqual(tc.description, description[d])
                iterations += 1
        except TapBailout:
            pass

        try:
            for d, tc in enumerate(TapDocumentIterator(doc)):
                self.assertEqual(tc.description, description[d])
                iterations += 1
        except TapBailout:
            pass

        self.assertEqual(iterations, 6)


class TestTapDocumentActualIterator(unittest.TestCase):

    def testIter(self):
        description = ["a", "b", "c", "d"]
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)

        for d in range(4):
            tc.description = description[d]
            doc.add_testcase(tc)
            if d == 2:
                doc.add_bailout(TapBailout("failure"))

        def iterate(doc):
            iterations = 0
            try:
                for d, tc in enumerate(TapDocumentActualIterator(doc)):
                    self.assertEqual(tc.description, description[d])
                    iterations += 1
            except TapBailout:
                return iterations
            return iterations

        self.assertEqual(iterate(doc), 3)

    def testIterWithoutBailout(self):
        description = ["a", "b", "c", "d"]
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)

        for d in range(4):
            tc.description = description[d]
            doc.add_testcase(tc)

        iterations = 0
        for d, tc in enumerate(TapDocumentActualIterator(doc)):
            self.assertEqual(tc.description, description[d])
            iterations += 1

        self.assertEqual(iterations, 4)


class TestTapDocumentFailedIterator(unittest.TestCase):

    def testIter(self):
        doc = TapDocument()
        doc.add_plan(1, 25)

        for i in range(20):
            tc = TapTestcase()
            tc.field = i % 2 == 1
            doc.add_testcase(tc)
            if i == 15:
                doc.add_bailout(TapBailout("fail"))

        iterations = 0
        for d, tc in enumerate(TapDocumentFailedIterator(doc)):
            self.assertFalse(tc.field)
            iterations += 1
        self.assertEqual(iterations, 10)


class TestTapParsing(unittest.TestCase):
    pass


class TestTapContextManager(unittest.TestCase):

    def testWrapper(self):
        with TapDocument() as tap:
            tap.plan(1, 4)
            tap.ok("a fine testcase").not_ok("a failed testcase")
            doc = tap.unwrap()

        self.assertEqual(doc.plan(), "1..4")
        self.assertIn("fine testcase", str(doc))
        self.assertIn("failed testcase", str(doc))


if __name__ == "__main__":
    unittest.main()
