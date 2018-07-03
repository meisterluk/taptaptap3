#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Check whether files in `examples` are read correctly"""

import os.path
import taptaptap3
import unittest

EXAMPLES = "../examples/"
e = lambda filename: os.path.join(EXAMPLES, filename + ".tap")


class TestExamples(unittest.TestCase):

    def test000(self):
        doc = taptaptap3.parse_file(e("000"))
        self.assertTrue(doc[1].field)
        self.assertEqual(doc[1].description, "This is fine")
        self.assertEqual(len(doc), 1)
        self.assertTrue(doc.valid())

    def test001(self):
        doc = taptaptap3.parse_file(e("001"))
        self.assertTrue(doc[1].field)
        self.assertEqual(doc[1].description, "This one's fine")
        self.assertEqual(doc.range(), (1, 1))
        self.assertEqual(doc.plan(), "1..1")
        self.assertFalse(doc.bailed())

    def test002(self):
        doc = taptaptap3.parse_file(e("002"))
        self.assertEqual(doc.version, 13)
        self.assertTrue(doc[1].field)
        self.assertEqual(doc[1].description, "This is fine")
        self.assertFalse(doc[1].todo)
        self.assertEqual(doc.range(), (1, 1))
        self.assertEqual(doc.plan(), "1..1")
        self.assertFalse(doc.bailed())

    def test003(self):
        doc = taptaptap3.parse_file(e("003"))
        self.assertFalse(doc.skip)
        self.assertEqual(doc.plan(), "1..4")
        self.assertEqual(doc.range(), (1, 4))
        self.assertEqual(doc.actual_plan(), "1..4")
        self.assertEqual(doc.actual_range(), (1, 4))
        self.assertEqual(len(doc), 4)
        self.assertEqual(doc.actual_length(), 4)
        self.assertEqual(doc[1].number, 1)

    def test004(self):
        doc = taptaptap3.parse_file(e("004"))
        self.assertFalse(doc[1].field)
        self.assertEqual(doc.count_not_ok(), 1)
        self.assertEqual(doc.count_todo(), 0)
        self.assertEqual(doc.count_skip(), 0)

    def test005(self):
        doc = taptaptap3.parse_file(e("005"))
        self.assertTrue(doc[1].field)
        self.assertFalse(doc[2].field)
        self.assertFalse(doc[3].todo)
        self.assertTrue(doc[4].todo)

    def test006(self):
        doc = taptaptap3.parse_file(e("006"))
        self.assertEqual(len(doc), 48)
        self.assertEqual(doc.actual_length(), 3)
        self.assertEqual(doc.range(), (1, 48))
        self.assertEqual(doc.actual_range(), (1, 48))
        self.assertEqual(doc[1].description, "Description # Directive")
        self.assertIn("...", doc[1].data[0])
        self.assertEqual(doc[48].description, "Description")
        self.assertIn("more tests...", doc[48].data[0])

    def test007(self):
        doc = taptaptap3.parse_file(e("007"))
        self.assertIn("Create a new", str(doc))

    def test008(self):
        doc = taptaptap3.parse_file(e("008"))
        self.assertFalse(doc.bailed())
        self.assertFalse(doc.valid())
        self.assertEqual(len(doc), 7)

    def test009(self):
        doc = taptaptap3.parse_file(e("009"))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertEqual(doc.plan(), "1..5")
        self.assertEqual(doc.actual_range(), (1, 5))

    def test010(self):
        doc = taptaptap3.parse_file(e("010"))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertTrue(doc.skip)
        self.assertEqual(len(doc), 0)

    def test011(self):
        doc = taptaptap3.parse_file(e("011"))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertTrue(doc.skip)
        self.assertEqual(len(doc), 0)
        self.assertEqual(doc.actual_length(), 6)
        self.assertEqual(doc.count_not_ok(), 1)
        self.assertEqual(doc.count_todo(), 0)

    def test012(self):
        doc = taptaptap3.parse_file(e("012"))
        self.assertTrue(doc[3].todo)

    def test013(self):
        doc = taptaptap3.parse_file(e("013"))
        self.assertTrue(len(doc), 9)
        self.assertTrue(doc.valid())

    def test014(self):
        doc = taptaptap3.parse_file(e("014"))
        self.assertTrue(len(doc), 6)
        self.assertTrue(doc.valid())
        self.assertEqual(doc[6].description, "Board size is 1")

    def test015(self):
        doc = taptaptap3.parse_file(e("015"))
        self.assertEqual(doc.version, 13)
        self.assertEqual(doc.plan(), "1..6")

    def test016(self):
        doc = taptaptap3.parse_file(e("016"))
        self.assertFalse(doc[2].field)
        self.assertEqual(
            doc[2].data[0],
            {
                "message": "First line invalid",
                "severity": "fail",
                "data": {"got": "Flirble", "expect": "Fnible"},
            },
        )
        self.assertFalse(doc[4].field)
        self.assertTrue(doc[4].todo)
        self.assertEqual(
            doc[4].data[0], {"message": "Can't make summary yet", "severity": "todo"}
        )

    def test017(self):
        doc = taptaptap3.parse_file(e("017"))
        self.assertEqual(doc.plan(), "1..2")
        self.assertEqual(doc[2].data[0], "  Text1\n")
        self.assertEqual(
            doc[2].data[1],
            {
                "message": "First line invalid",
                "severity": "fail",
                "data": {"got": "Flirble", "expect": "Fnible"},
            },
        )
        self.assertEqual(doc[2].data[2], "  not ok Text2\n")
        self.assertEqual(doc[2].data[3], {"key": "value"})
        self.assertTrue(doc.valid())

    def test018(self):
        doc = taptaptap3.parse_file(e("018"))
        self.assertRaises(taptaptap3.exc.TapInvalidNumbering, lambda: doc.valid())

    def test019(self):
        doc = taptaptap3.parse_file(e("019"))
        self.assertEqual(doc.version, 13)
        self.assertTrue(doc[7].field)
        self.assertEqual(doc[7].description, "The object isa Board")
        self.assertFalse(doc[2].todo)
        self.assertEqual(doc.range(), (1, 12))
        self.assertEqual(doc.plan(), "1..12")
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())

    def test020(self):
        doc = taptaptap3.parse_file(e("020"))
        self.assertEqual(len(doc), 0)

    def test021(self):
        doc = taptaptap3.parse_file(e("021"))
        self.assertEqual(len(doc), 573)
        self.assertEqual(doc.actual_length(), 1)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc[1].field)
        self.assertIn("Couldn't connect to database.", doc.bailout_message())

        def iterate():
            for _ in doc:
                pass

        self.assertRaises(taptaptap3.exc.TapBailout, iterate)

    def test022(self):
        doc = taptaptap3.parse_file(e("022"))
        self.assertEqual(len(doc), 2)
        self.assertEqual(doc.actual_length(), 2)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc.valid())
        # require first bailout message
        self.assertEqual(doc.bailout_message(), "Couldn't connect to database.")

    def test023(self):
        doc = taptaptap3.parse_file(e("023"))
        self.assertTrue(doc.valid())

    def test024(self):
        # The ultimate Pile of Poo test
        # http://intertwingly.net/blog/2013/10/22/The-Pile-of-Poo-Test
        doc = taptaptap3.parse_file(e("024"))
        self.assertTrue(doc[1].description, "💩")
        self.assertTrue(doc.valid())

    def test025(self):
        doc = taptaptap3.parse_file(e("025"))
        self.assertTrue(doc[1].field)
        self.assertTrue(doc[2].field)
        self.assertFalse(doc[3].field)
        self.assertFalse(doc[4].field)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc.valid())
        self.assertEqual(doc.bailout_message(), "Stopped iteration")

    def test026(self):
        doc = taptaptap3.parse_file(e("026"))
        self.assertFalse(doc.valid())


if __name__ == "__main__":
    unittest.main()
