#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    proc.py
    ~~~~~~~

    Procedural API for TAP file generation.
    Call plan, comment, ok, not_ok and write in the sequence order::

        (plan (ok | not_ok | comment)+ bailout? write)*

    Other control flows might work, but are not officially supported.
    All functions except `write` return the document;
    thus allows method chaining.

    (c) BSD 3-clause.
"""

from .impl import TapDocument, TapContext


# global state

doc = TapDocument()
context = TapContext(doc)
plan_written = False

def doc():
    """API to retrieve the document we are working with.
    Can be used to apply methods not provided by the procedural API
    or test the state of the document.
    """
    return doc

def plan(start=None, end=None, tests=None):
    """Define how many tests you want to run.
    Either provide `start` & `end` or `tests` attributes as integers.
    """
    global plan_written, doc, context

    if plan_written:
        # dump old instance and create a new one
        doc = TapDocument()
        context = TapContext(doc)
        plan_written = False

    with context as tap_doc:
        plan(start, end, tests)

    plan_written = True

def comment(cmt):
    """Add a comment at the current position."""
    global context

    with context as tap_doc:
        tap_doc.comment(cmt)

def ok(comment, data=None, skip=False, todo=False):
    """Add information about a succeeded testcase"""
    global context

    with context as tap_doc:
        tap_doc.ok(comment, data, skip, todo)

def not_ok(comment, data=None, skip=False, todo=False):
    """Add information about a failed testcase. Always returns True"""
    global context

    with context as tap_doc:
        tap_doc.not_ok(comment, data, skip, todo)

def bailout(comment=u''):
    """Trigger a bailout"""
    global context

    with context as tap_doc:
        tap_doc.bailout(comment)

def write():
    """Write the document to stdout"""
    global context

    with context as tap_doc:
        return tap_doc.write()
