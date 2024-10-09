#!/usr/bin/env python3

import sys
import taptaptap3

if __name__ == "__main__":
    doc = taptaptap3.parse_file(sys.argv[-1])
    print(str(doc), end=" ")
    if doc and doc.bailed():
        sys.exit(-2)
    sys.exit(0) if doc and doc.valid() else sys.exit(-1)
