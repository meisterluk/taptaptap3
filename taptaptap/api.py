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

from .impl import TapTestcase, TapDocument, TapDocumentIterator, TapWrapper
from .impl import TapDocumentTokenizer, TapDocumentParser, TapDocumentValidator
from .exc import TapBailout

__all__ = ['parse_string', 'parse_file', 'validate', 'harness', 'TapWriter',
           'TapCreator', 'SimpleTapCreator', 'UnittestResult', 'UnittestRunner']


# Nice-to-use functions for TapDocument creation

def parse_string(string, lenient=True):
    """Parse the given `string` and return its TapDocument instance.

    :param unicode string:      A string to parse
    :param bool lenient:        Lenient parsing? If so errors are thrown late.
    :return TapDocument doc:    TapDocument instance for this string
    """
    tokenizer = TapDocumentTokenizer()
    tokenizer.from_string(string)
    parser = TapDocumentParser(tokenizer, lenient)
    return parser.document


def parse_file(filepath, lenient=True):
    """Parse a TAP file and return its TapDocument instance.

    :param unicode filepath:    A valid filepath for `open`
    :param bool lenient:        Lenient parsing? If so errors are thrown late.
    :return TapDocument doc:    TapDocument instance for this file
    """
    tokenizer = TapDocumentTokenizer()
    tokenizer.from_file(filepath)
    parser = TapDocumentParser(tokenizer, lenient)
    return parser.document


def validate(doc):
    """Does TapDocument `doc` represent a successful test run?"""
    validator = TapDocumentValidator(doc)
    return validator.valid()


def harness(doc):
    """Return a representation of `doc` like perl's Test.Harness.
    See http://search.cpan.org/dist/JS-Test-Simple/lib/JS/Test/Harness.pod#Failure
    Be aware that the example output shows a summary for a *set* of TAP files.
    We return the output for *one* TAP file and its testcases.
    """
    out = u''
    succeeded = []
    failed = []
    last_tc = None
    try:
        for tc in TapDocumentIterator(doc):
            if not tc.field:
                failed.append(tc.number)
                out += u'{:.<23}not ok\n'.format(tc.description)
            else:
                succeeded.append(tc.number)
                out += u'{:.<23}ok\n'.format(tc.description)
            last_tc = tc.description

        if not failed:
            out += u'All tests successful.\n'
        else:
            cfailed = len(failed)
            ctotal = len(doc)

            out += u'FAILED tests {}\n'.format(' '.join(map(str, failed)))
            out += u'\tFailed {}/{} tests, {:.2f}%% okay.'.format(cfailed,
                   ctotal, 100.0 * cfailed / ctotal)

    except TapBailout:
        cfailed = len(failed)
        ctotal = len(doc)

        out += u'DIED. FAILED tests {}'.format(', '.join(map(str, failed)))
        out += u'        Failed {}/{} tests, {:2f}%% okay' \
               .format(cfailed, ctotal, 1.0 * cfailed / ctotal)

        out += u'Failed Test         Total Fail  Failed  List of Failed'
        out += u'-' * 61
        out += u'{: <20}{: >5}{: >5} {: >7} {}'.format(last_tc, ctotal,
               cfailed, 100.0 * cfailed / ctotal, ' '.join(map(str, failed)))


class TapWriter(object):
    """A small API to write TAP output. It features almost the same
    like `TapWrapper`, but delays any execution until the finalization step.
    """

    def __init__(self):
        self._plan, self.skip = None, None
        self.entries, self.comments = [], []
        self.version = None

    def plan(self, first=None, last=None, skip=u'', tests=None,
             tapversion=None):
        """Define plan. Provide integers `first` and `last` XOR `tests`.
        `skip` is a non-empty message if the whole testsuite was skipped.
        """
        if all([v is None for v in [first, last, tests]]):
            raise ValueError("Provide either first and last params or tests")
        elif tests is not None:
            self._plan = (1, int(tests))
        else:
            self._plan = (first, last)

        self.skip = skip
        self.version = tapversion

        return self

    def testcase(self, ok=True, description=u'', skip=u'', todo=u''):
        """Add a testcase entry to the TapDocument"""
        tc = TapTestcase()
        tc.field = ok
        tc.description = description
        if skip:
            tc.skip = skip
        if todo:
            tc.todo = todo

        self.entries.append(tc)
        self.comments.append(None)
        return self

    def ok(self, description=u'', skip=False, todo=False):
        """Add a succeeded testcase entry to the TapDocument"""
        return self.testcase(True, description, skip, todo)

    def not_ok(self, description=u'', skip=False, todo=False):
        """Add a failed testcase entry to the TapDocument"""
        return self.testcase(False, description, skip, todo)

    def bailout(self, comment, data=None):
        """Add Bailout to document"""
        bailout = TapBailout(comment)
        if data:
            bailout.data = data
        self.entries.append(bailout)
        return self

    def write(self, line):
        """Add a comment at the current position"""
        self.comments.append(line)
        return self

    def finalize(self):
        """Finalize this TapDocument"""
        doc = TapDocument()
        if self.version:
            doc.add_version_line(self.version)
        if self._plan:
            doc.add_plan(self._plan[0], self._plan[1], self.skip)

        cmt_iter = iter(self.comments)

        for cmt in cmt_iter:
            if cmt is not None:
                doc.add_header_line(cmt)
            else:
                break

        for entry in self.entries:
            # collect comments
            cmts = []
            for cmt in cmt_iter:
                if cmt is not None:
                    cmts.append(cmt)
                else:
                    break

            # add testcases and bailouts to TapDocument
            if entry.is_testcase:
                entry.data = cmts
                doc.add_testcase(entry)
            else:
                doc.add_bailout(entry)

        self._doc = doc
        return self

    @property
    def doc(self):
        self.finalize()
        return self._doc

    def __unicode__(self):
        return unicode(self.doc)

    def __str__(self):
        return str(self.doc)


def TapCreator(func):
    """TAP document decorator.
    The wrapped function can optionally accept parameters first, last or tests
    to specify the number of tests. Use it like

        >>> @taptaptap.TapCreator
        >>> def runTests():
        >>>     yield {'ok': True, 'description': '1 + 1 == 2'}
        >>>     yield {'ok': True,
        >>>            'description': 'E = mc^2', 'skip': 'Still in discussion'}
        >>>     yield {'ok': False, 'description': '2 + 2 = 5',
        >>>            'todo': 'Fix surveillance state'}
        >>>     raise taptaptap.exc.TapBailout("System failure!")
        >>>
        >>> print runTests()
        1..3
        ok 1 - 1 + 1 == 2
        ok 2 - E = mc^2  # SKIP Still in discussion
        not ok 3 - 2 + 2 = 5  # TODO Fix surveillance state
        Bail out! System failure!
    """
    def inner(*args, **kwargs):
        writer = TapWriter()
        try:
            count = 0
            for result in func(*args, **kwargs):
                result['ok']  # required param

                data = result.get('data')
                if 'data' in result:
                    del result['data']

                writer.testcase(**result)
                if data:
                    for cmt in data:
                        writer.write(cmt)
                count += 1

        except TapBailout as e:
            writer.bailout(e.message, data=e.data)

        finally:
            if 'first' in kwargs and 'last' in kwargs:
                writer.plan(first=int(kwargs['first']),
                            last=int(kwargs['last']))
            elif 'tests' in kwargs:
                writer.plan(tests=int(kwargs['tests']))
            else:
                writer.plan(tests=count)

        return unicode(writer)

    return inner


def SimpleTapCreator(func):
    """TAP document decorator.
    The wrapped function can optionally accept parameters first, last or tests
    to specify the number of tests. Use it like

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

    def inner(*args, **kwargs):
        tcs = []
        try:
            version = kwargs.get('version', TapDocument.DEFAULT_VERSION)
            skip = kwargs.get('skip', False)
            doc = TapDocument(version=version, skip=skip)

            count = 0
            for result in func(*args, **kwargs):
                tc = TapTestcase()
                tc.field = bool(result)
                tcs.append(tc)
                count += 1

        except TapBailout as bailout:
            tcs.append(bailout)

        finally:
            # retrieve plan
            metadata = {}
            if 'skip_comment' in kwargs:
                metadata['skip_comment'] = kwargs['skip_comment']
            
            if 'first' in kwargs and 'last' in kwargs:
                metadata['first'] = int(kwargs['first'])
                metadata['last'] = int(kwargs['last'])

            elif 'tests' in kwargs:
                metadata['first'] = 1
                metadata['last'] = int(kwargs['tests'])

            else:
                metadata['first'] = 1
                metadata['last'] = count

            doc.add_plan(**metadata)

            # retrieve testcases
            for tc in tcs:
                if tc.is_testcase:
                    doc.add_testcase(tc)
                else:
                    doc.add_bailout(tc)

        return unicode(doc)

    return inner


class UnittestResult(unittest.result.TestResult):
    def __init__(self, count_tests=None):
        assert count_tests is not None, "`count_tests` must be a number"
        super(UnittestResult, self).__init__()
        self.doc = TapWrapper()

        self.doc.plan(first=1, last=count_tests)

    def addSuccess(self, test):
        super(UnittestResult, self).addSuccess(test)

        self.doc.ok(test.shortDescription())
        self.doc.write(unicode(test).strip())

    def addError(self, test, err):
        super(UnittestResult, self).addError(test, err)
        exctype, value, tracebk = err

        self.doc.not_ok(test.shortDescription())
        self.doc.write(value.strip())
        self.doc.write(unicode(test))

    def addFailure(self, test, err):
        super(UnittestResult, self).addFailure(test, err)
        exctype, value, tracebk = err

        self.doc.not_ok(test.shortDescription())
        self.doc.write(value.strip())
        self.doc.write(unicode(test))

    def addSkip(self, test, reason):
        super(UnittestResult, self).addSkip(test, reason)

        self.doc.not_ok(test.shortDescription(), skip=reason)
        self.doc.write(unicode(test).strip())

    def addTime(self, seconds):
        self.doc.write("Running time: {} seconds".format(seconds))

    def printErrorList(self, flavour, errors):
        for test, err in errors:
            self.doc.write("-" * 35)
            self.doc.write("%s: %s" % (flavour, self.getDescription(test)))
            self.doc.write("%s" % err)
            self.doc.write("-" * 35)

    def write(self, stream=sys.stderr):
        self.doc.finalize()
        print(self.doc, file=stream)


class UnittestRunner(object):
    """A unittest runner class for python's `unittest` module"""

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
