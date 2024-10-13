#!/usr/bin/env python3

"""Merge two TAP files"""

import sys
import typing
import argparse
import taptaptap3

from ..impl import TapDocument


def read_stdin() -> typing.Optional[TapDocument]:
    """Read and parse string from stdin"""
    content = u""
    encoding = sys.stdin.encoding or sys.getdefaultencoding()
    for line in sys.stdin:
        content += line.decode(encoding)
    return taptaptap3.parse_string(content)


def main(args: argparse.Namespace) -> None:
    if len(args.files) <= 1:
        raise ValueError("You must at least specify two TAP files")

    docs = [(read_stdin() if f == "-" else taptaptap3.parse_file(f)) for f in args.files]
    doc3 = taptaptap3.merge(*docs)

    if args.outfile:
        with open(args.outfile, "w") as fp:
            fp.write(doc3)
    else:
        print(doc3, file=sys.stderr)


def cli() -> int:
    # command line parameter parsing
    parser = argparse.ArgumentParser(description="Merge two or more TAP files.")
    parser.add_argument(
        "files", metavar="F", nargs="+", help="At least two TAP files to merge"
    )
    parser.add_argument(
        "-o",
        "--outputfile",
        dest="outfile",
        action="store",
        help="write to filepath instead of stdout",
    )

    main(parser.parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(cli() or 0)