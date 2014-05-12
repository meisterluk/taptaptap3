#!/usr/bin/env python
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

from .impl import TapDocument, TapDocumentValidator
from .api import TapWriter


writer = None
counter = 0  # counter for tcs, if no plan provided
planned = False  # was a plan written yet?

def _create():
    global writer
    if writer is None:
        writer = TapWriter()

def plan(first=None, last=None, skip=u'', tests=None,
         tapversion=TapDocument.DEFAULT_VERSION):
    """Define a plan. Provide integers `first` and `last` XOR `tests`.
    `skip` is a non-empty message if the whole testsuite was skipped.
    """
    _create()
    writer.plan(first, last, skip, tests, tapversion)

def write(line):
    """Add a comment at the current position"""
    _create()
    writer.write(line)

def ok(description=u'', skip=False, todo=False):
    """Add a succeeded testcase entry"""
    _create()

    if skip == True:
        skip = u' '
    elif skip == False:
        skip = u''

    if todo == True:
        todo = u' '
    elif todo == False:
        todo = u''

    writer.testcase(True, description, skip, todo)

def not_ok(description=u'', skip=False, todo=False):
    """Add a failed testcase entry"""
    _create()
    writer.testcase(False, description, skip, todo)

def bailout(comment=''):
    """Add Bailout to document"""
    _create()
    writer.bailout(comment)

def out():
    _create()
    print(unicode(writer))
