#!/usr/bin/env python

import sys
import taptaptap

if __name__ == '__main__':
    doc = taptaptap.parse_file(sys.argv[-1])
    print str(doc),
    if doc.bailed():
        sys.exit(-2)
    sys.exit(0) if doc.valid() else sys.exit(-1)
