#!/usr/bin/env python

import codecs
import os.path
import taptaptap
import unittest

e = lambda x: os.path.join('../examples', x)


def parse_file(x):
    with codecs.open(x, encoding='utf-8') as fp:
        content = u''
        for line in fp.readlines():
            if line and not line.startswith('## '):
                content += line
        return taptaptap.parse_string(content)


class MergeTapDocuments(unittest.TestCase):
    def test_merge(self):
        doc1 = parse_file(e('012.tap'))
        doc2 = parse_file(e('006.tap'))
        doc3 = parse_file(e('017.tap'))
        doc4 = parse_file(e('020.tap'))
        doc5 = parse_file(e('022.tap'))
        doc6 = parse_file(e('024.tap'))
        ref = parse_file(e('026.tap'))

        self.assertFalse(doc1.valid())
        self.assertFalse(doc2.valid())
        self.assertTrue(doc3.valid())
        self.assertTrue(doc4.valid())
        self.assertFalse(doc5.valid())
        self.assertTrue(doc6.valid())
        self.assertFalse(ref.valid())
        self.assertTrue(ref.bailed())

        merged = taptaptap.merge(doc1, doc2, doc3, doc4, doc5, doc6)

        self.assertFalse(merged.valid())
        self.assertTrue(merged.bailed())
        self.assertFalse(merged.skip)
        self.assertEquals(len(merged), 57)
        self.assertEquals(merged.actual_length(), 12)
        self.assertEquals(merged.range(), (1, 57))
        self.assertEquals(merged.actual_range(), (1, 57))
        self.assertEquals(merged.count_not_ok(), 2)
        self.assertEquals(merged.count_todo(), 2)
        self.assertEquals(merged.count_skip(), 0)
        self.assertEquals(merged.bailout_message(),
                          u"Couldn't connect to database.")
        self.assertIn(56, merged)

        self.assertEquals(unicode(merged), unicode(ref))


if __name__ == '__main__':
    unittest.main()
