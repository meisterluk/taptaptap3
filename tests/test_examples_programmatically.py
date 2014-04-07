#!/usr/bin/env python

"""Contains all testcases which are read with `from_file`
using the files in the `examples` directory
"""

import sys
sys.path.append('../..')

import os.path
import subprocess
import taptaptap


EXAMPLES = "../examples/"

# testsuite

def verify(document, codes):
    try:
        for code in codes:
            exec 'assert {}'.format(code) in {}, {'doc': document}
    except AssertionError:
        raise AssertionError("Failed: " + code)

def read(filepath, testcases):
    path = os.path.join(EXAMPLES, filepath)
    reader = TapDocumentReader().from_file(path, lenient=True)

    doc = reader.document
    verify(doc, testcases)
    return doc


# testcases

TESTCASES = {
    '001.tap': [
        'doc.get_plan() == u"1..4"', 'not doc.valid()', 'not doc.bailed()',
        'doc[1].field', 'doc[1].number == 1',
        'doc[1].description == u"Input file opened"', 'not doc[2].field',
        'not doc[2].todo', 'not doc[2].skip', 'not doc[2].data',
        'doc[3].field', 'doc[3].description == u"Read the rest of the file"',
        'not doc[3].todo', 'not doc[3].skip', 'not doc[3].data',
        'not doc[4].field', 'doc[4].description == u"Summarized correctly"',
        'doc[4].todo', 'not doc[4].skip'],
    '002.tap': [
        'doc.get_actual_range() == "1..3"', 'doc.get_plan() == "1..48"',
        'not doc.valid()', 'not doc.bailed()', 'doc[1].field',
        'doc[1].description == u"Description"', 'doc[1].directive == u""'
        'list(doc).get(40, 244) == 244', 'doc[47].description == u"Description"',
        'doc[48].description == u"Description"', 'doc[48].data == [u"moretests...."]',
        'list(doc).get(100, 245) == 245'
    ],
    '003.tap': [
        'doc.get_actual_plan() == u"1..6"', 'doc.valid()', 'not doc.bailed()',
        'doc[1].field', 'doc[1].description == u"The object isa Board"',
        'doc[2].field', 'doc[2].description == u"Board size is zero"',
        'doc[3].field', 'doc[3].description == u"The object isa Tile"',
        'doc[4].field', 'not doc[4].todo', 'not doc[4].skip', 'not doc[4].data'
    ],
    '004.tap': [
        'doc.get_plan() == u"1..7"', 'not doc.valid()', 'not doc.bailed()',
        'doc[1].data == [u"need to ping 6 servers"]',
        'doc[2].description == u"pinged diamond"', 'not doc[4].field',
        'doc[7].description == u"pinged gold"'
    ],
    '005.tap': ['not doc.valid()', 'doc.bailed()'],
    '006.tap': ['doc.valid()', 'doc[2].skip', 'not doc[3].description'],
    '007.tap': ['doc.valid()', 'len(doc) == 0', 'doc.skip'],
    '009.tap': [
        'doc.valid()', 'not doc.bailed()', 'doc[1].field',
        'doc[1].description == u"created Board"', 'doc[2].field',
        'doc[9].description == u"board has 7 tiles + starter tile"'
    ],
    '010.tap': [
        'doc.version == 13',
        'doc[5].description == u"Placing the tile produces no error"'
    ],
    '011.tap': [
        'not doc.valid()', 'doc.bailed()', 'not doc[2].field', 'doc[3].field',
        'doc[2].data == [{u"message": u"First line invalid", u"data": ' +
        '{u"got": u"Flirble", u"expect": u"Fnible"}, u"severity": u"fail"}',
        'doc[4].data == [{u"message": u"Can\'t make summary yet", u"severity": u"todo"}]'
    ]
    '013.tap': [
        'not doc.valid()', 'not doc.bailed()', 'doc.get_plan() == u"1..2"',
        'doc[1].field', 'doc[1].description == u"Multidata test"',
        'not doc[2].field', 'doc[2].description == u"2 texts and 2 data dumps"',
        'doc[2].data == [u"Text1", {u"message": u"First line invalid", ' +
        'u"severity": u"fail", u"data": {u"got": "Flirble", u"expect": u"Fnible"}},' +
        'u"not ok Text2", {u"key": u"value"}]'
    ]
}

if __name__ == '__main__':
    for filename, tcs in TESTCASES.iteritems():
        read(filename, tcs)
