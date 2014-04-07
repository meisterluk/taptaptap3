#!/usr/bin/env python

import sys
sys.path.append('../..')

from taptaptap import YamlData, TapStream, TapContext
from taptaptap import TapDocument, TapNumbering, TapTestcase
from taptaptap import TapDocumentIterator, TapDocumentActualIterator
from taptaptap import TapDocumentFailedIterator
from taptaptap.exc import *

import unittest


def parse(source, strict=False):
    TapDocumentReader().from_string(source, lenient=not strict)

class TestTapDocument(unittest.TestCase):
    def testEmptyDocument(self):
        doc = TapDocument()
        self.assertEquals(doc.version, 13)
        self.assertEquals(doc.skip, False)
        self.assertEquals(len(doc), 0)
        self.assertEquals(unicode(doc), u'1..0\n')

    def testConstructor(self):
        doc = TapDocument(version=13)
        self.assertEquals(doc.version, 13)

        doc = TapDocument(skip=True)
        self.assertTrue(doc.skip)

        doc.add_testcase(TapTestcase())
        self.assertIn(u'skip', unicode(doc).lower())

    def testSet(self):
        doc = TapDocument()

        doc.set_version(12)
        self.assertEquals(doc.version, 12)

        doc.set_skip(True)
        self.assertTrue(doc.skip)
        doc.set_skip(False)
        self.assertFalse(doc.skip)

    def testAdd(self):
        doc = TapDocument()

        doc.add_plan(1, 5, u'SKIP wip')
        self.assertIn(u'wip', unicode(doc))
        self.assertIn(u'1..5', unicode(doc))

        tc = TapTestcase()
        tc.field = True
        tc.number = 1
        tc.description = 'TC #1'
        tc.data = [">>> int('88t')",
                   "Traceback (most recent call last):",
                   '  File "<stdin>", line 1, in <module>',
                   "ValueError: invalid literal for int() with base 10: '88t'",
                   {'locals': ['int']}]

        doc.add_testcase(tc)
        self.assertIn(u'wip', unicode(doc))
        self.assertIn(u'1..5', unicode(doc))
        self.assertIn(u'...', unicode(doc))
        self.assertIn(u'88t', unicode(doc))
        self.assertIn(u'locals', unicode(doc))

        doc.add_bailout(TapBailout('Filesystem crashed'))
        self.assertIn(u'Bail out! Filesystem crashed', unicode(doc))

    def testAdd(self):
        doc = TapDocument()

        doc.add_version_line(12)
        self.assertEquals(doc.version, 12)

        doc.add_header_line('Hello World')
        doc.add_header_line('Embrace!')
        self.assertIn(u'Hello World', unicode(doc))
        self.assertIn(u'Embrace!', unicode(doc))

    def testLength(self):
        doc = TapDocument()
        doc.add_plan(3, 7)

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_bailout(TapBailout('FS problem'))

        self.assertEquals(len(doc), 2)
        self.assertEquals(doc.actual_length(), 5)

    def testRangeAndPlan(self):
        doc = TapDocument()

        self.assertEquals(doc.range(), (1, 0))
        self.assertEquals(doc.actual_range(), (1, 0))
        self.assertEquals(doc.plan(), '1..0')
        self.assertEquals(doc.actual_plan(), '1..0')

        doc.add_plan(3, 7)

        self.assertEquals(doc.range(), (3, 7))
        self.assertEquals(doc.actual_range(), (1, 0))
        self.assertEquals(doc.plan(), '3..7')
        self.assertEquals(doc.actual_plan(), '1..0')

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_bailout(TapBailout('FS problem'))

        self.assertEquals(doc.range(), (3, 7))
        self.assertEquals(doc.actual_range(), (3, 4))
        self.assertEquals(doc.plan(), '3..7')
        self.assertEquals(doc.actual_plan(), '3..4')

    def testIn(self):
        doc = TapDocument()

        self.assertFalse(1 in doc)
        self.assertFalse(2 in doc)
        self.assertFalse(42 in doc)

        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())

        self.assertTrue(1 in doc)
        self.assertTrue(2 in doc)
        self.assertFalse(3 in doc)

        tc = TapTestcase()
        tc.number = 5
        doc.add_testcase(tc)

        self.assertTrue(1 in doc)
        self.assertTrue(2 in doc)
        self.assertTrue(5 in doc)
        self.assertFalse(3 in doc)
        self.assertFalse(4 in doc)
        self.assertFalse(6 in doc)

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

        self.assertEquals(doc.count_failed(), 2)
        self.assertEquals(doc.count_todo(), 3)
        self.assertEquals(doc.count_skip(), 1)

    def testBailout(self):
        doc = TapDocument()
        self.assertFalse(doc.bailed())

        doc.add_testcase(TapTestcase())
        self.assertFalse(doc.bailed())

        doc.add_bailout(TapBailout('FS crash'))
        self.assertTrue(doc.bailed())

        doc.add_bailout(TapBailout('Another crash'))
        self.assertTrue(doc.bailed())

        self.assertEquals(doc.bailout_message(), 'FS crash')

    def testValid(self):
        # valid iff
        #   no bailout was thrown AND
        #   document itself is skipped OR
        #   all TCs exist AND
        #     are 'ok' OR
        #     skipped

        # default
        doc = TapDocument()
        self.assertTrue(doc.valid())

        # bailout
        # must work without a plan
        doc.set_skip(True)
        doc.add_bailout(TapBailout('filesystem problem'))
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
        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_plan(1, 4)
        self.assertTrue(doc.valid())

        # all tcs are ok
        doc = TapDocument()
        tc = TapTestcase()
        tc.field = False
        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_testcase(TapTestcase())
        doc.add_testcase(tc)
        doc.add_plan(1, 4)
        self.assertFalse(doc.valid())

        # all tcs are skipped
        tc = TapTestcase()
        tc.field = False
        tc.skip = True
        doc = TapDocument()
        doc.set_skip(False)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_testcase(tc)
        doc.add_plan(1, 5)
        self.assertTrue(doc.valid())

        doc.add_bailout(TapBailout('System crashed'))
        self.assertFalse(doc.valid())

class TestTapDocumentIterator(unittest.TestCase):
    def testIter(self):
        description = ['a', 'b', 'c', 'd']
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)
        for d in range(4):
            tc.description = description[d]
            doc.add_testcase(tc)
            if d == 2:
                doc.add_bailout(TapBailout('failure'))

        for d, tc in enumerate(iter(doc)):
            self.assertEquals(tc.description, description[d])

        for d, tc in enumerate(TapDocumentIterator(doc)):
            self.assertEquals(tc.description, description[d])

class TestTapDocumentActualIterator(unittest.TestCase):
    def testIter(self):
        description = ['a', 'b', 'c', 'd']
        doc = TapDocument()
        tc = TapTestcase()
        doc.add_plan(1, 20)

        for d in range(4):
            tc.description = description[d]
            doc.add_testcase(tc)
            if d == 3:
                doc.add_bailout(TapBailout('failure'))

        iterations = 0
        for d, tc in enumerate(TapDocumentActualIterator(doc)):
            self.assertEquals(tc.description,
                d >= 4 and description[d] or None
            )
            iterations += 1
        self.assertEquals(iterations, 20)

class TestTapDocumentFailedIterator(unittest.TestCase):
    def testIter(self):
        doc = TapDocument()
        doc.add_plan(1, 25)

        for i in range(20):
            tc = TapTestcase()
            tc.field = (i % 2 == 1)
            doc.add_testcase(tc)
            if i == 15:
                doc.add_bailout(TapBailout('fail'))

        iterations = 0
        for d, tc in enumerate(TapDocumentFailedIterator(doc)):
            self.assertFalse(tc.field)
            iterations += 1
        self.assertEquals(iterations, 13)

class TestTapParsing(unittest.TestCase):
    pass

class TestTapStream(unittest.TestCase):
    def testStreaming(self):
        s = TapStream('T')
        s.write('AP ver')
        s.write('sion 13\n1..2')
        s.write('\nok 24 description\n')
        s.write('Traceback\n  System\nValueError\nn')
        s.write('ot ok')
        self.assertEquals(s.read(), '')

class TestTapContext(unittest.TestCase):
    def testContext(self):
        with TapDocument() as tap:
            tap.plan(1, 4)
            tap.ok("a fine testcase")
            tap.not_ok("a failed testcase")
            doc = tap.get()
        self.assertEquals(doc.plan(), '1..4')
        self.assertIn(u'fine testcase', unicode(doc))
        self.assertIn(u'failed testcase', unicode(doc))

if __name__ == '__main__':
    unittest.main()
