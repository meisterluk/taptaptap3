#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    api.py
    ~~~~~~

    Various APIs to use taptaptap.

    (c) BSD 3-clause.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import sys
import time
import unittest

from . import TapTestcase, TapDocument, TapDocumentReader


__ALL__ = ['parse_file', 'parse_string', 'TapWriter',
           'TapCreator', 'SimpleTapCreator']

# Simply function to create TapDocument instances

def parse_string(tap_string):
    """Parse a TAP document from the given unicode string."""
    reader = TapDocumentReader()
    reader.from_string(tap_string)
    return reader.document


def parse_file(filepath):
    """Parse the TAP document at the given `filepath`."""
    reader = TapDocumentReader()
    reader.from_file(filepath)
    return reader.documentTapDocumentReader




class TapWriter(object):
    """A simplified API to write TAP output.
    Use `ok` and `not_ok` methods to write testcase results.
    """

    def __init__(self):
        self.counter = 1
        self.doc = TapDocument()

    @staticmethod
    def create_directive(skip=u'', todo=u''):
        space = (skip and todo) and u' ' or u''
        skip = u'SKIP ' + unicode(skip)
        todo = u'TODO ' + unicode(todo)

        return (skip + space + todo).strip()

    def _create(self, field, description=u'', directive=u'', data=u''):
        """Create a new TAP testcase.

        :param field:           "ok" | "not ok"
        :param description:     description of TAP testcase
        :param directive:       something like "TODO work in progress" ...
                                "TODO" | "SKIP"   must occur
        :param data:            arbitrary data associated with this entry
        """
        tc = TapTestcase()
        tc.field = field
        if description:
            tc.description = description
        if directive:
            tc.directive = directive
        if data:
            tc.data = data

        self.doc.add_testcase(tc)

    def bailout(self, comment):
        """Create a bailout"""
        self.doc.add_bailout(comment)

    def ok(self, description=u'', data=u'', skip=u'', todo=u''):
        self._create('ok', description, self.create_directive(skip, todo), data)

    def not_ok(self, description=u'', data=u'', skip=u'', todo=u''):
        self._create('not ok', description,
            self.create_directive(skip, todo), data)

    def __unicode__(self):
        return unicode(self.doc)

    def __str__(self):
        return str(self.doc)


def TapCreator(func, *tap_args, **tap_kwargs):
    """TAP document decorator.
    Use it like

        >>> @taptaptap.TapCreator
        >>> def runTests():
        >>>     yield {'success': True, 'description': '1 + 1 == 2'}
        >>>     yield {'success': True,
        >>>            'description': 'E = mc^2', 'skip': 'Still in discussion'}
        >>>     yield {'success': False, 'description': '2 + 2 = 5',
        >>>            'todo': 'Fix surveillance state'}
        >>>
        >>> print runTests()
        1..3
        ok 1 - 1 + 1 == 2
        ok 2 - E = mc^2  # SKIP Still in discussion
        not ok 3 - 2 + 2 = 5  # TODO Fix surveillance state
    """
    writer = TapWriter(*tap_args, **tap_kwargs)

    # TODO: exception triggers bailout
    def inner(*args, **kwargs):
        for result in func(*args, **kwargs):
            success = result['success']  # required param
            del result['success']
            if success:
                writer.ok(**result)
            else:
                writer.not_ok(**result)

        return unicode(writer)

    return inner


def SimpleTapCreator(func, *tap_args, **tap_kwargs):
    """TAP document decorator.
    Use it like

        >>> @taptaptap.SimpleTapCreator
        >>> def runTests():
        >>>     yield True
        >>>     yield True
        >>>     yield False
        >>>
        >>> print runTests()
        1..3
        ok
        ok
        not ok
    """
    writer = TapWriter(*tap_args, **tap_kwargs)

    def inner(*args, **kwargs):
        result = func(*args, **kwargs)
        if result:
            writer.ok()
        elif result:
            writer.not_ok()

        return unicode(writer)

    return inner


class UnittestResult(unittest.result.TestResult):
    def __init__(self, count_tests=None):
        assert count_tests is not None, "`count_tests` must be a number"
        super(UnittestResult, self).__init__()
        self.doc = TapDocument()

        with self.doc as d:
            d.plan(tests=count_tests)

    def addSuccess(self, test):
        super(UnittestResult, self).addSuccess(test)
        with self.doc as d:
            data = unicode(test).strip() + '\n'
            d.ok(test.shortDescription(), data=data)

    def addError(self, test, err):
        super(UnittestResult, self).addError(test, err)
        exctype, value, tracebk = err
        with self.doc as d:
            d.not_ok(test.shortDescription(), data=value.strip() + '\n')
            d.comment(unicode(test))

    def addFailure(self, test, err):
        super(UnittestResult, self).addFailure(test, err)
        exctype, value, tracebk = err
        with self.doc as d:
            d.not_ok(test.shortDescription(), data=value.strip() + '\n')
            d.comment(unicode(test))

    def addSkip(self, test, reason):
        super(UnittestResult, self).addSkip(test, reason)
        with self.doc as d:
            data = unicode(test).strip() + '\n'
            d.not_ok(test.shortDescription(), data=data, skip=reason)

    def addTime(self, seconds):
        with self.doc as d:
            d.comment("Running time: {} seconds".format(seconds))

    def printErrorList(self, flavour, errors):
        with self.doc as d:
            for test, err in errors:
                d.comment("-" * 35)
                d.comment("%s: %s" % (flavour, self.getDescription(test)))
                d.comment("%s" % err)
                d.comment("-" * 35)

    def write(self, stream=sys.stderr):
        print(self.doc, file=stream)


class UnittestRunner(object):
    """A not-that-fancy unittest runner class for python's `unittest` module"""

    def __init__(self, stream=sys.stderr):
        self.stream = stream

    def run(self, test):
        """Run testcase/testsuite `test`"""
        nr_testcases = test.countTestCases()
        result = UnittestResult(count_tests=nr_testcases)
        start = time.time()

        startTestRun = getattr(result, 'startTestRun', None)
        if startTestRun is not None:
            startTestRun()
        try:
            test(result)
        finally:
            stopTestRun = getattr(result, 'stopTestRun', None)
            if stopTestRun is not None:
                stopTestRun()
        
        if nr_testcases > 0:
            result.addTime(time.time() - start)

        result.write()
        return result
