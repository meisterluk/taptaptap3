#!/usr/bin/env python

import taptaptap
import unittest

INPUT1 = '''TAP version 13
1..5
ok 1 - Input file opened
not ok 2 - First line of the input valid
  ---
  message: 'First line invalid'
  severity: fail
  data:
    got: 'Flirble'
    expect: 'Fnible'
  ...
ok 3 - Read the rest of the file
not ok 4 - Summarized correctly # TODO Not written yet
  ---
  message: "Can't make summary yet"
  severity: todo
  ...'''

INPUT2 = '''
TAP version 13
1..48
ok 1 Description # Directive
# Diagnostic
  ---
  message: 'Failure message'
  severity: fail
  data:
    got:
      - 1
      - 3
      - 2
    expect:
      - 1
      - 2
      - 3
  ...
ok 47 Description
ok 48 Description
more tests....
'''

class MergeTapDocuments(unittest.TestCase):
    def test_merge(self):
      doc1 = taptaptap.parse_string(INPUT1)
      doc2 = taptaptap.parse_string(INPUT2)

      self.assertEqual(doc1.version, 13)
      self.assertEqual(doc1.version, 13)
      self.assertEquals(doc1[1].description, 'Input file opened')

      doc3 = doc1.merge(doc2)

      self.assertEquals(doc3[53].data, u'more tests....\n')

      s = str(doc3)
      self.assertEquals(doc3.get_plan(), u'1..53')
      self.assertIn('# Diagnostic', s)

if __name__ == '__main__':
    unittest.main()
