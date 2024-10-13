#!/usr/bin/env python3

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
import typing


writer: typing.Optional[TapWriter] = None
counter: int = 0  # counter for tcs, if no plan provided
planned: bool = False  # was a plan written yet?


def _create() -> None:
    global writer
    if writer is None:
        writer = TapWriter()


def plan(
    first: typing.Optional[int]=None, last: typing.Optional[int]=None, skip: str="", tests: typing.Optional[int]=None, tapversion: int=TapDocument.DEFAULT_VERSION
) -> bool:
    """Define a plan. Provide integers `first` and `last` XOR `tests`.
    `skip` is a non-empty message if the whole testsuite was skipped.
    """
    _create()
    writer.plan(first, last, skip, tests, tapversion)
    return True


def write(line: str) -> None:
    """Add a comment at the current position"""
    _create()
    writer.write(line)


def ok(description: str="", skip: typing.Union[str, bool]=False, todo: typing.Union[str, bool]=False) -> bool:
    """Add a succeeded testcase entry"""
    if skip is True:
        skip = " "
    elif skip is False:
        skip = ""
    if todo is True:
        todo = " "
    elif todo is False:
        todo = ""

    _create()
    writer.testcase(True, description, skip, todo)
    return True


def not_ok(description: str="", skip: typing.Union[str, bool]=False, todo: typing.Union[str, bool]=False) -> bool:
    """Add a failed testcase entry"""
    if skip is True:
        skip = " "
    elif skip is False:
        skip = ""
    if todo is True:
        todo = " "
    elif todo is False:
        todo = ""

    _create()
    writer.testcase(False, description, skip, todo)
    return True


def bailout(comment: str="") -> bool:
    """Add Bailout to document"""
    _create()
    writer.bailout(comment)
    return True


def out() -> None:
    """Print TAP output to stderr"""
    _create()
    print(str(writer), file=sys.stderr)
