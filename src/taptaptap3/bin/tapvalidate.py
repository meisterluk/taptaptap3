#!/usr/bin/env python3

"""
Does TAP file indicate an error?

Reads a TAP file and exit status indicates success:
  0:  everything is fine
 -1:  some testcase is missing or failed
 -2:  A bailout was thrown
If some text occurs at stderr, taptaptap3 has a problem
"""

import sys
import argparse
import taptaptap3


def main(args: argparse.Namespace) -> int:
    if args.report == "-":
        content = u""
        encoding = sys.stdin.encoding or sys.getdefaultencoding()
        for line in sys.stdin:
            content += line.decode(encoding)
        doc = taptaptap3.parse_string(content)
    else:
        doc = taptaptap3.parse_file(args.report)
    if doc.bailed():
        return -2
    elif doc.valid():
        return 0
    else:
        return -1


def cli() -> int:
    # command line parameter parsing
    desc = ""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report", metavar="report", help="the TAP file to read, dash for stdin"
    )

    return main(parser.parse_args())

if __name__ == "__main__":
    sys.exit(cli() or 0)