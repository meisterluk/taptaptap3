#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Check whether files in `examples` are read correctly"""

import os.path
import taptaptap
import unittest

EXAMPLES = "../examples/"
e = lambda filename: os.path.join(EXAMPLES, filename + u'.tap')


class TestExamples(unittest.TestCase):
    def test000(self):
        doc = taptaptap.parse_file(e('000'))
        self.assertTrue(doc[1].field)
        self.assertEquals(doc[1].description, u'This is fine')
        self.assertEquals(len(doc), 1)
        self.assertTrue(doc.valid())

    def test001(self):
        doc = taptaptap.parse_file(e('001'))
        self.assertTrue(doc[1].field)
        self.assertEquals(doc[1].description, u"This one's fine")
        self.assertEquals(doc.range(), (1, 1))
        self.assertEquals(doc.plan(), u'1..1')
        self.assertFalse(doc.bailed())

    def test002(self):
        doc = taptaptap.parse_file(e('002'))
        self.assertEquals(doc.version, 13)
        self.assertTrue(doc[1].field)
        self.assertEquals(doc[1].description, u"This is fine")
        self.assertFalse(doc[1].todo)
        self.assertEquals(doc.range(), (1, 1))
        self.assertEquals(doc.plan(), u'1..1')
        self.assertFalse(doc.bailed())

    def test003(self):
        doc = taptaptap.parse_file(e('003'))
        self.assertFalse(doc.skip)
        self.assertEquals(doc.plan(), u'1..4')
        self.assertEquals(doc.range(), (1, 4))
        self.assertEquals(doc.actual_plan(), u'1..4')
        self.assertEquals(doc.actual_range(), (1, 4))
        self.assertEquals(len(doc), 4)
        self.assertEquals(doc.actual_length(), 4)
        self.assertEquals(doc[1].number, 1)

    def test004(self):
        doc = taptaptap.parse_file(e('004'))
        self.assertFalse(doc[1].field)
        self.assertEquals(doc.count_not_ok(), 1)
        self.assertEquals(doc.count_todo(), 0)
        self.assertEquals(doc.count_skip(), 0)

    def test005(self):
        doc = taptaptap.parse_file(e('005'))
        self.assertTrue(doc[1].field)
        self.assertFalse(doc[2].field)
        self.assertFalse(doc[3].todo)
        self.assertTrue(doc[4].todo)

    def test006(self):
        doc = taptaptap.parse_file(e('006'))
        self.assertEquals(len(doc), 48)
        self.assertEquals(doc.actual_length(), 3)
        self.assertEquals(doc.range(), (1, 48))
        self.assertEquals(doc.actual_range(), (1, 48))
        self.assertEquals(doc[1].description, u'Description # Directive')
        self.assertIn(u'...', doc[1].data[0])
        self.assertEquals(doc[48].description, u'Description')
        self.assertIn(u'more tests...', doc[48].data[0])

    def test007(self):
        doc = taptaptap.parse_file(e('007'))
        self.assertIn(u'Create a new', unicode(doc))

    def test008(self):
        doc = taptaptap.parse_file(e('008'))
        self.assertFalse(doc.bailed())
        self.assertFalse(doc.valid())
        self.assertEquals(len(doc), 7)

    def test009(self):
        doc = taptaptap.parse_file(e('009'))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertEquals(doc.plan(), u'1..5')
        self.assertEquals(doc.actual_range(), (1, 5))

    def test010(self):
        doc = taptaptap.parse_file(e('010'))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertTrue(doc.skip)
        self.assertEquals(len(doc), 0)

    def test011(self):
        doc = taptaptap.parse_file(e('011'))
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())
        self.assertTrue(doc.skip)
        self.assertEquals(len(doc), 0)
        self.assertEquals(doc.actual_length(), 6)
        self.assertEquals(doc.count_not_ok(), 1)
        self.assertEquals(doc.count_todo(), 0)

    def test012(self):
        doc = taptaptap.parse_file(e('012'))
        self.assertTrue(doc[3].todo)

    def test013(self):
        doc = taptaptap.parse_file(e('013'))
        self.assertTrue(len(doc), 9)
        self.assertTrue(doc.valid())

    def test014(self):
        doc = taptaptap.parse_file(e('014'))
        self.assertTrue(len(doc), 6)
        self.assertTrue(doc.valid())
        self.assertEquals(doc[6].description, u'Board size is 1')

    def test015(self):
        doc = taptaptap.parse_file(e('015'))
        self.assertEquals(doc.version, 13)
        self.assertEquals(doc.plan(), u'1..6')

    def test016(self):
        doc = taptaptap.parse_file(e('016'))
        self.assertFalse(doc[2].field)
        self.assertEquals(doc[2].data[0],
            {'message': 'First line invalid', 'severity': 'fail', 'data':
                {'got': 'Flirble', 'expect': 'Fnible'}})
        self.assertFalse(doc[4].field)
        self.assertTrue(doc[4].todo)
        self.assertEquals(doc[4].data[0],
            {'message': "Can't make summary yet", 'severity': 'todo'})

    def test017(self):
        doc = taptaptap.parse_file(e('017'))
        self.assertEquals(doc.plan(), u'1..2')
        self.assertEquals(doc[2].data[0], u'  Text1\n')
        self.assertEquals(doc[2].data[1], {
            'message': 'First line invalid',
            'severity': 'fail',
            'data': {'got': 'Flirble', 'expect': 'Fnible'}
        })
        self.assertEquals(doc[2].data[2], '  not ok Text2\n')
        self.assertEquals(doc[2].data[3], {'key': 'value'})
        self.assertTrue(doc.valid())

    def test018(self):
        doc = taptaptap.parse_file(e('018'))
        self.assertRaises(taptaptap.exc.TapInvalidNumbering, lambda: doc.valid())

    def test019(self):
        doc = taptaptap.parse_file(e('019'))
        self.assertEquals(doc.version, 13)
        self.assertTrue(doc[7].field)
        self.assertEquals(doc[7].description, u"The object isa Board")
        self.assertFalse(doc[2].todo)
        self.assertEquals(doc.range(), (1, 12))
        self.assertEquals(doc.plan(), u'1..12')
        self.assertFalse(doc.bailed())
        self.assertTrue(doc.valid())

    def test020(self):
        doc = taptaptap.parse_file(e('020'))
        self.assertEquals(len(doc), 0)

    def test021(self):
        doc = taptaptap.parse_file(e('021'))
        self.assertEquals(len(doc), 573)
        self.assertEquals(doc.actual_length(), 1)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc[1].field)
        self.assertIn(u"Couldn't connect to database.", doc.bailout_message())

        def iterate():
            for tc in doc:
                pass

        self.assertRaises(taptaptap.exc.TapBailout, iterate)

    def test022(self):
        doc = taptaptap.parse_file(e('022'))
        self.assertEquals(len(doc), 2)
        self.assertEquals(doc.actual_length(), 2)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc.valid())
        # require first bailout message
        self.assertEquals(doc.bailout_message(), u"Couldn't connect to database.")

    def test023(self):
        doc = taptaptap.parse_file(e('023'))
        self.assertTrue(doc.valid())

    def test024(self):
        # The ultimate Pile of Poo test
        # http://intertwingly.net/blog/2013/10/22/The-Pile-of-Poo-Test
        doc = taptaptap.parse_file(e('024'))
        self.assertTrue(doc[1].description, u'💩')
        self.assertTrue(doc.valid())

    def test025(self):
        doc = taptaptap.parse_file(e('025'))
        self.assertTrue(doc[1].field)
        self.assertTrue(doc[2].field)
        self.assertFalse(doc[3].field)
        self.assertFalse(doc[4].field)
        self.assertTrue(doc.bailed())
        self.assertFalse(doc.valid())
        self.assertEquals(doc.bailout_message(), u'Stopped iteration')

    def test026(self):
        doc = taptaptap.parse_file(e('026'))
        self.assertFalse(doc.valid())


if __name__ == '__main__':
    unittest.main()
