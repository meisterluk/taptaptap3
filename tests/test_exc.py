#!/usr/bin/env python3

from taptaptap3 import TapDocumentValidator, parse_string
from taptaptap3.exc import TapMissingPlan, TapInvalidNumbering
from taptaptap3.exc import TapBailout, TapParseError

import io
import pickle
import unittest


def parse(source: str, strict=False):
    return parse_string(source, lenient=not strict)


def validate_manually(doc):
    # raises errors in case of errors
    val = TapDocumentValidator(doc)
    val.sanity_check()
    return val.valid()


class TestExceptions(unittest.TestCase):

    def testParseError(self):
        two_tcs1 = "1..1\nnot ok 1\nnot ok 1\n"
        no_plan = "not ok\n"
        no_integer_version = "TAP version 13h\n1..1\nok\n"
        invalid_plan = "1..1b\nok\n"
        negative_plan = "3..0\n "

        # two_tcs1
        two_tcs1_doc = parse(two_tcs1, False)
        self.assertRaises(TapInvalidNumbering, validate_manually, two_tcs1_doc)
        two_tcs1_doc = parse(two_tcs1, True)
        self.assertRaises(TapInvalidNumbering, validate_manually, two_tcs1_doc)

        no_plan_doc = parse(no_plan, False)
        self.assertRaises(TapMissingPlan, validate_manually, no_plan_doc)
        no_plan_doc = parse(no_plan, True)
        self.assertRaises(TapMissingPlan, validate_manually, no_plan_doc)

        self.assertRaises(TapParseError, parse, no_integer_version, True)

        invalid_plan_doc = parse(invalid_plan, False)
        self.assertRaises(TapMissingPlan, validate_manually, invalid_plan_doc)
        self.assertRaises(TapParseError, parse, invalid_plan, True)

        neg_plan_doc = parse(negative_plan, False)
        validate_manually(neg_plan_doc)
        self.assertRaises(TapParseError, parse, negative_plan, True)

    def testBailout(self):
        try:
            raise TapBailout("Message")
            self.assertTrue(False)
        except TapBailout as e:
            self.assertIn("Bail out!", str(e))

    def testPickle(self):

        def trypickle(obj: TapBailout):
            dump_file = io.BytesIO()
            pickle.dump(obj, dump_file)
            dump_file.seek(0)
            return pickle.load(dump_file)

        bailout = TapBailout("Hello World")
        bailout.data = ["Hi", "ho"]
        bailout = trypickle(bailout)
        self.assertEqual(bailout.msg, "Hello World")
        self.assertEqual(";".join(bailout.data), "Hi;ho")


if __name__ == "__main__":
    unittest.main()
