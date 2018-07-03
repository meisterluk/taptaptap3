#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    proc.py
    ~~~~~~~

    Procedural API for TAP file generation (ie. TapWriter on module-level).
    Call plan, comment, ok, not_ok and write in the sequence order::

        plan? (write | ok | not_ok)+ bailout? out

    Other control flows might work, but are not officially supported.

    (c) BSD 3-clause.
"""


from .impl import TapDocument
from .api import TapWriter

import sys


writer = None
counter = 0  # counter for tcs, if no plan provided
planned = False  # was a plan written yet?


def _create():
    global writer
    if writer is None:
        writer = TapWriter()


def plan(
    first=None, last=None, skip="", tests=None, tapversion=TapDocument.DEFAULT_VERSION
):
    """Define a plan. Provide integers `first` and `last` XOR `tests`.
    `skip` is a non-empty message if the whole testsuite was skipped.
    """
    _create()
    writer.plan(first, last, skip, tests, tapversion)
    return True


def write(line):
    """Add a comment at the current position"""
    _create()
    writer.write(line)


def ok(description="", skip=False, todo=False):
    """Add a succeeded testcase entry"""
    _create()

    if skip is True:
        skip = " "
    elif skip is False:
        skip = ""

    if todo is True:
        todo = " "
    elif todo is False:
        todo = ""

    writer.testcase(True, description, skip, todo)
    return True


def not_ok(description="", skip=False, todo=False):
    """Add a failed testcase entry"""
    _create()
    writer.testcase(False, description, skip, todo)
    return True


def bailout(comment=""):
    """Add Bailout to document"""
    _create()
    writer.bailout(comment)
    return True


def out():
    """Print TAP output to stderr"""
    _create()
    print(str(writer), file=sys.stderr)
