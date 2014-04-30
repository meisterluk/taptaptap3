#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    impl.py
    ~~~~~~~

    TAP file handling implementation.

    * 'range' is a tuple of two numbers. 'plan' is a string.
      They both represent TAP testcase numberings.

    * 'actual' in identifiers refers to the absolute number of testcases
      which must not correspond to the testcases specified by the plan::

        1..50
        ok 1 first
        ok 25 second

      Actual number of testcases is 2. Number of testcases is 50.

    * '1..0' exceptionally represents '0 testcases'. In general
      a negative range triggers a warning if lenient is set to
      False (non-default).

    (c) BSD 3-clause.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

from .exc import TapParseError, TapBailout, TapMissingPlan, TapInvalidNumbering

import re
import os
import sys
import copy
import logging
import yamlish
import collections

__all__ = ['YamlData', 'TapTestcase', 'TapActualNumbering', 'TapNumbering',
           'TapDocument', 'TapDocumentIterator', 'TapDocumentActualIterator',
           'TapDocumentFailedIterator', 'TapDocumentTokenizer',
           'TapDocumentParser', 'TapContext', 'validate', 'repr_harness',
           'tapmerge', 'parse_file', 'parse_string']


STR_ENC = sys.getdefaultencoding()


class YamlData(object):
    """YAML data storage"""
    def __init__(self, data):
        self.data = data

    def __iter__(self):
        return iter(self.data)

    def __unicode__(self):
        return yamlish.dumps(self.data)


class TapTestcase(object):
    """Object representation of an entry in a TAP file"""
    is_testcase = True
    is_bailout = False

    def __init__(self, field=None, number=None, description=u''):
        # test line
        self._field = field
        self._number = number
        self.description = description
        self._directives = {'skip': [], 'todo': []}
        # data
        self._data = []

    @staticmethod
    def indent(text, indent=2):
        """Indent all lines of ``text`` by ``indent`` spaces"""
        return re.sub('(^|\n)(?!\n|$)', '\\1' + (' ' * indent), text)

    @property
    def field(self):
        """A TAP field specifying whether testcase succeeded"""
        return self._field

    @field.setter
    def field(self, value):
        errmsg = "field value must be 'ok' or 'not ok', not {!r}".format(value)
        try:
            if value in [None, True, False]:
                self._field = value
            elif value.rstrip() == 'ok':
                self._field = True
            elif value.rstrip() == 'not ok':
                self._field = False
            else:
                raise ValueError(errmsg)
        except AttributeError:
            raise ValueError(errmsg)

    @field.deleter
    def field(self):
        self._field = None

    @property
    def number(self):
        """A TAP testcase number"""
        return self._number

    @number.setter
    def number(self, value):
        if value is None:
            self._number = value
            return
        try:
            value = int(value)
        except TypeError:
            raise ValueError("Argument must be integer")
        if value < 0:
            raise ValueError("Testcase number must not be negative")
        self._number = value

    @number.deleter
    def number(self):
        self._number = None

    @property
    def directive(self):
        """A TAP directive like 'TODO work in progress'"""
        out = u''
        for skip_msg in self._directives['skip']:
            out += u'SKIP {} '.format(skip_msg.strip())
        for todo_msg in self._directives['todo']:
            out += u'TODO {} '.format(todo_msg.strip())
        return out and out[:-1] or u''

    @directive.setter
    def directive(self, value):
        # reset
        self._directives['skip'] = []
        self._directives['todo'] = []

        if not value:
            return

        delimiters = ['skip', 'todo']
        value = value.lstrip('#\t ')
        parts = re.split('(' + '|'.join(delimiters) + ')', value, flags=re.I)
        parts = [p for p in parts if p]

        if not parts or parts[0].lower() not in delimiters:
            raise ValueError('Directive must start with SKIP or TODO')

        for i in range(0, len(parts), 2):
            category = parts[i].lower()
            msg = parts[i + 1]
            self._directives[category].append(msg)

    @directive.deleter
    def directive(self):
        self._directives = {}

    @property
    def data(self):
        """Annotated data (like a backtrace) to the testcase"""
        return self._data

    @data.setter
    def data(self, value):
        msg = "If you set data explicitly, it has to be a list"
        assert hasattr(value, '__iter__'), msg

        self._data = copy.deepcopy(value)

    @data.deleter
    def data(self):
        self._data = []

    @property
    def todo(self):
        """Is a TODO flag annotated to this testcase?"""
        return bool(self._directives['todo'])

    @todo.setter
    def todo(self, what):
        """Add a TODO flag to this testcase.

        :param unicode what:    Which work is still left?
        """
        self._directives['todo'].append(what) if what else None

    @property
    def skip(self):
        """Is a SKIP flag annotated to this testcase?"""
        return bool(self._directives['skip'])

    @skip.setter
    def skip(self, why):
        """Add a SKIP flag to this testcase.

        :param unicode why:    Why shall this testcase be skipped?
        """
        self._directives['skip'].append(why) if why else None

    def copy(self):
        """Return a copy of myself"""
        tc = TapTestcase()
        tc.__setstate__(self.__getstate__())
        return tc

    def __getstate__(self):
        """Return object state for external storage"""
        return {
            'field': self.field,
            'number': self.number,
            'description': self.description or u'',
            'directives': self._directives,
            'data': self.data
        }

    def __setstate__(self, obj):
        """Import data using the provided object"""
        self.field = obj['field']
        self.number = obj['number']
        self.description = obj['description']
        self._directives = obj['directives']
        self.data = obj['data']

    def __repr__(self):
        """Representation of this object"""
        field = 'ok' if self.field else 'not ok'
        num = '' if self.number is None else ' #{}'.format(self._number)
        todo_skip = ''

        if self.todo and self.skip:
            todo_skip = ' with TODO and SKIP flag'
        elif self.todo:
            todo_skip = ' with TODO flag'
        elif self.skip:
            todo_skip = ' with SKIP flag'

        return u'<TapTestcase {}{}{}>'.format(field, num, todo_skip)

    def __unicode__(self):
        """TAP testcase representation as a unicode object"""
        num, desc, directive = self.number, self.description, self.directive

        out = u'ok ' if self.field else u'not ok '
        if num is not None:
            out += unicode(num) + u' '
        if desc:
            out += u'- {} '.format(desc)
        if directive:
            out += u'# {} '.format(directive)
        out = out.rstrip()
        if self.data:
            data = [unicode(d) for d in self.data]
            out += os.linesep + self.indent((os.linesep).join(data), 2)

        if out.endswith(os.linesep):
            return out
        else:
            return out + os.linesep

    def __str__(self):
        return unicode(self).encode(STR_ENC)


class TapNumbering(object):
    """TAP testcase numbering. In TAP documents it is called 'the plan'."""

    def __init__(self, first=None, last=None, tests=None, lenient=True):
        """Constructor. Provide `first` and `last` XOR a number of `tests`.

        `first` and `last` are testcase numbers. Both inclusive.

        If `lenient` is False, a decreasing range (except '1..0')
        will raise a TapInvalidNumbering Exception.
        Otherwise it will just be normalized (set `last` to `first`).
        """
        arg_errmsg = 'Either provide a first and last or a number of tests'
        if first and last and tests:
            raise ValueError(arg_errmsg)

        if first is not None and last is not None:
            self.first = int(first)
            self.length = int(last) - int(first) + 1

            if int(last) == 0 and int(first) == 1:
                self.length = 0
            elif int(last) < int(first):
                self.length = 0
                if not lenient:
                    msg = 'range {}..{} is decreasing'.format(first, last)
                    msg = 'Invalid testcase numbering: ' + msg
                    raise TapInvalidNumbering(msg)

        elif tests is not None:
            self.first = 1
            self.length = int(tests)

        else:
            raise ValueError(arg_errmsg)

        assert(self.first >= 0 and self.length >= 0)

    def __len__(self):
        return self.length

    def __nonzero__(self):
        return True

    def __contains__(self, tc_number):
        """Is `tc_number` within this TapNumbering range?"""
        return self.first <= tc_number and tc_number < self.first + self.length

    def enumeration(self):
        """Get enumeration for the actual tap plan."""
        return list(range(self.first, self.first + self.length))

    def inc(self):
        """Increase numbering for one new testcase"""
        self.length += 1

    def normalized_plan(self):
        """Return a normalized plan where first=1"""
        return '{:d}..{:d}'.format(1, self.length)

    def range(self):
        """Get range of this numbering: (min, max)"""
        return (self.first, self.first + self.length - 1)

    def __getstate__(self):
        return {'first': self.first, 'length': self.length}

    def __setstate__(self, state):
        self.first = state['first']
        self.length = state['length']

    def __iter__(self):
        return iter(range(self.first, self.first + self.length))

    def __unicode__(self):
        """Return unicode representation of plan.
        If it was initially a decreasing range, first=last now.
        """
        return '{:d}..{:d}'.format(self.first, self.first + self.length - 1)

    def __repr__(self):
        return '<TapNumbering {}>'.format((self.first, self.length))


class TapActualNumbering(list):
    """TAP testcase numbering. Wrapper for a sequence of testcase numbers."""
    pass


class TapDocument(object):
    """An object representing a TAP document"""
    DEFAULT_VERSION = 13

    def __init__(self, version=DEFAULT_VERSION, skip=False):
        # testcases and bailouts
        self.entries = []
        self.metadata = {
            # version line
            'version': version,
            'version_written': False,
            # comment lines before first testcase
            'header_comment': u'',
            # TAP plan
            'numbering': None,
            'plan_at_beginning': True,
            'skip': bool(skip),
            'skip_comment': u''
        }

    def __nonzero__(self):
        return True

    @property
    def version(self):
        """Get TAP version for this document"""
        return self.metadata['version']

    @property
    def skip(self):
        """Was this document skipped in the test run?"""
        return self.metadata['skip']

    # set information

    def set_version(self, version=DEFAULT_VERSION):
        """Set TAP version of this document"""
        self.metadata['version'] = int(version)

    def set_skip(self, skip_comment=u''):
        """Set skip annotation for this document"""
        if skip_comment:
            self.metadata['skip'] = True
            self.metadata['skip_comment'] = skip_comment
        else:
            self.metadata['skip'] = False

    def add_version_line(self, version=DEFAULT_VERSION):
        """Add information of version lines like 'TAP version 13'"""
        self.set_version(version)
        self.metadata['version_written'] = True

    def add_header_line(self, line):
        """Add header comment line for TAP document"""
        if line.count(os.linesep) > 1:
            raise ValueError("Header line should only be 1 (!) line")
        self.metadata['header_comment'] += unicode(line).rstrip()
        self.metadata['header_comment'] += os.linesep

    def add_plan(self, first, last, skip_comment=u'', at_beginning=True):
        """Add information of a plan like '1..3 # SKIP wip'"""
        self.metadata['plan_at_beginning'] = bool(at_beginning)
        self.metadata['numbering'] = TapNumbering(first=first, last=last)
        if skip_comment:
            self.set_skip(skip_comment)

    def add_testcase(self, tc):
        """Add a ``TapTestcase`` or ``TapBailout`` instance `tc`"""
        self.entries.append(copy.deepcopy(tc))

    def add_bailout(self, bo):
        """Add a ``TapBailout`` instance `bo` to this document"""
        self.entries.append(bo.copy())

    # processing

    @staticmethod
    def create_plan(first, last, comment=u'', skip=False):
        plan = u'{:d}..{:d}'.format(first, last)

        if os.linesep in comment:
            raise ValueError('Plan comment must not contain newline')

        if skip:
            if not comment.strip():
                comment = ' # SKIP'
            elif 'skip' not in comment.lower():
                comment = ' # SKIP ' + comment
            else:
                comment = ' # ' + comment.strip()
        else:
            comment = ''

        return plan + comment

    # retrieve information

    def __len__(self):
        """Return number of testcases in this document"""
        if self.metadata['numbering']:
            return len(self.metadata['numbering'])
        return self.actual_length()

    def actual_length(self):
        """Return actual number of testcases in this document"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase:
                count += 1
        return count

    def range(self):
        """Get range like ``(1, 2)`` for this document"""
        if not self.metadata['numbering']:
            return (1, 0)

        return self.metadata['numbering'].range()

    def actual_range(self):
        """Get actual range"""
        if not self.metadata['numbering'] or not self.entries:
            return (1, 0)

        validator = TapDocumentValidator(self)
        enum = validator.enumeration()
        return (min(enum), max(enum))

    def plan(self, comment=u'', skip=False):
        """Get plan for this document"""
        options = {'comment': self.metadata['skip_comment'],
                   'skip': self.metadata['skip']}
        return self.create_plan(*self.range(), **options)

    def actual_plan(self):
        """Get actual plan for this document"""
        options = {'comment': self.metadata['skip_comment'],
                   'skip': self.metadata['skip']}
        return self.create_plan(*self.actual_range(), **options)

    def count_failed(self):
        """How many testcases which are 'not ok' are there?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and not entry.field:
                count += 1
        return count

    def count_todo(self):
        """How many testcases are still 'todo'?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.todo:
                count += 1
        return count

    def count_skip(self):
        """How many testcases got skipped in this document?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.skip:
                count += 1
        return count

    def bailed(self):
        """Was a Bailout called at some point in time?"""
        for entry in self.entries:
            if entry.is_bailout:
                return True
        return False

    def bailout_message(self):
        """Return the first bailout message of document or None"""
        for entry in self.entries:
            if entry.is_bailout:
                return entry.message
        return None

    def valid(self):
        """Is this document valid?"""
        validator = TapDocumentValidator(self)
        return validator.valid()

    def __contains__(self, num):
        """Does testcase exist in document?
        It exists iff a testcase object with this number or number 'None'
        exists as entry in doc which corresponds to this number.
        """
        validator = TapDocumentValidator(self)
        enum = validator.enumeration()
        try:
            if self.entries[enum.index(int(num))] is None:
                return False
            else:
                return True
        except (ValueError, IndexError):
            return False

    def __getitem__(self, num):
        """Return testcase with the given number.
        Returns copy of testcase, returns None (if range specifies existence)
        or raises IndexError (if testcase does not exist at all).
        """
        try:
            num = int(num)
        except ValueError:
            return False

        validator = TapDocumentValidator(self)
        enum = validator.enumeration()
        if 0 <= num < len(enum):
            nr = 0
            for entry in self.entries:
                if entry.is_testcase:
                    if nr == enum[num]:
                        e = copy.deepcopy(entry)
                        e.number = num
                        return e
                    nr += 1
        else:
            raise IndexError("No testcase with number {} exists".format(num))

    def __iter__(self):
        """Get iterator for testcases"""
        return TapDocumentIterator(self)

    def __getstate__(self):
        """Return state of this object"""
        state = copy.copy(self.metadata)
        state['entries'] = [entry.__getstate__() for entry in self.entries]
        if state['numbering']:
            state['numbering'] = state['numbering'].__getstate__()
        return state

    def __setstate__(self, state):
        """Restore object's state from `state`"""
        self.entries = []
        self.metadata = {}

        for key, value in state.iteritems():
            if key == u'entries':
                for entry in value:
                    tc = TapTestcase()
                    tc.__setstate__(entry)
                    self.entries.append(tc)
            elif key == u'numbering':
                self.metadata[key] = TapNumbering(tests=0)
                self.metadata[key].__setstate__(value)
            else:
                self.metadata[key] = value

        keys_exist = ['version', 'version_written', 'header_comment',
                      'numbering', 'skip', 'skip_comment']
        for key in keys_exist:
            if key not in self.metadata:
                raise ValueError('Missing key {} in state'.format(key))

    def copy(self):
        """Return a copy of this object"""
        obj = TapDocument()
        obj.__setstate__(self.__getstate__())
        return obj

    def __enter__(self):
        """Return context for this document"""
        return TapContext(self)

    def __exit__(self, exc_type, exc_value, tracebk):
        """Finalize context for this document"""
        pass

    def __str__(self):
        """String representation of TAP document"""
        return unicode(self).encode(STR_ENC)

    def __unicode__(self):
        """Unicode representation of TAP document"""
        out = u''
        # version line
        if self.metadata['version_written']:
            out += u'TAP version {:d}'.format(self.metadata['version'])
            out += os.linesep
        # header comments
        out += self.metadata['header_comment']
        # [possibly] plan
        if self.metadata['plan_at_beginning']:
            out += self.plan() + os.linesep
        # testcases and bailouts
        for entry in self.entries:
            out += unicode(entry)
        # [possibly] plan
        out += self.plan() if not self.metadata['plan_at_beginning'] else u''

        return out


class TapDocumentValidator(object):
    """TAP testcase numbering. In TAP documents it is called 'the plan'."""

    def __init__(self, doc, lenient=True):
        """Constructor.

        :param TapDocument doc:   the TAP document to validate
        """
        self.lenient = lenient
        self.skip = doc.skip
        self.bailed = doc.bailed()

        if not doc.metadata['numbering']:
            msg = "Document cannot be validated. Document requires plan."
            raise TapMissingPlan(msg)

        # retrieve numbers and range
        self.numbers = []
        self.validity = True
        for entry in doc.entries:
            if entry.is_testcase:
                self.numbers.append(entry.number)
                if not entry.field and not entry.skip:
                    self.validity = False
        self.range = doc.range()

        # prepare enumeration
        self.enum = None

    def test_range_validity(self):
        """Is `range` valid for `numbers`?"""
        # more testcases than allowed
        length = self.range[1] - self.range[0] + 1
        if length < len(self.numbers):
            msg = "More testcases provided than allowed by plan"
            raise TapInvalidNumbering(msg)

        # Is some given number outside of range?
        for nr in self.numbers:
            if nr is not None:
                if not (self.range[0] <= nr <= self.range[1]):
                    msg = "Testcase number {} is outside of plan {}..{}"
                    raise TapInvalidNumbering(msg.format(nr, *self.range))

        ## Is some given number used twice?
        ## Remark. Is tested by enumerate 
        #numbers = set()
        #for index, nr in enumerate(self.numbers):
        #    if nr is not None:
        #        if nr in numbers:
        #            msg = "Testcase number {} used twice at indices {} and {}"
        #            first_index = self.numbers.index(nr)
        #            raise ValueError(msg.format(nr, index, first_index))
        #        numbers.add(nr)

    @staticmethod
    def enumerate(numbers, first=1, lenient=False):
        """Take a sequence of positive numbers and assign numbers,
        where None is given::

            >>> enumerate([1, 2, None, 4])
            [1, 2, 3, 4]
            >>> enumerate([None, None, 2])
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
            ValueError: Testcase number 2 was already used
            >>> enumerate([None, None, 2], lenient=True)
            [1, 3, 2]

        Post conditions:
        * Always the smallest possible integers are assigned (starting with `first`).
          But if a high integer is given, this one is used instead.
        * Returns a sequence of positive numbers or raises a ValueError.
        """
        assigned = set()
        fixed = set()
        sequence = []
        next_number = None

        reuse_errmsg = "Testcase number {} was already used"

        def get_next_number(nr):
            nr = first
            while nr in assigned or nr in fixed:
                nr += 1
            return nr

        for nr in numbers:
            if nr is None:
                next_number = get_next_number(next_number)

                assigned.add(next_number)
                sequence.append(next_number)
                next_number += 1
            else:
                if nr in fixed:
                    raise ValueError(reuse_errmsg.format(nr))
                elif nr in assigned:
                    if not lenient:
                        raise ValueError(reuse_errmsg.format(nr))
                    next_number = get_next_number(next_number)

                    # replace "nr" with "next_number" in assigned and sequence
                    assigned.remove(nr)
                    fixed.add(next_number)
                    sequence = [e == nr and next_number or e for e in sequence]
                    sequence.append(nr)

                    next_number += 1
                else:
                    fixed.add(nr)
                    sequence.append(nr)
                    if nr > next_number:
                        next_number = nr + 1

        return sequence

    def all_exist(self):
        """Do all testcases in specified `range` exist?"""
        self.enumeration()
        try:
            for i in range(self.range[0], self.range[1] + 1):
                self.enum.index(i)
            return True
        except ValueError:
            return False

    def __nonzero__(self):
        return self.valid()

    def enumeration(self, lenient=True):
        """Get enumeration for given `self.numbers`. Enumeration is the list
        of testcase numbers like `self.numbers` but with Nones eliminated.
        Thus it maps all indices of testcase entries to testcase numbers.

        :param bool lenient:    Shall I fix simple errors myself?
        """
        if not self.enum:
            self.test_range_validity()
            self.enum = self.enumerate(self.numbers, self.range[0], lenient)

        return self.enum

    def __iter__(self):
        return iter(self.enumeration())

    def __repr__(self):
        return '<TapDocumentValidator {} {}{}>'.format(self.numbers, self.range,
            self.enum and ' with enumeration' or '')

    def sanity_check(self, lenient=True):
        """Raise any errors which indicate that this document is wrong.
        This method performs a subset of checks of `valid`, but raises errors
        with meaningful messages unlike `valid` which just returns False.

        :param bool lenient:    Shall I ignore more complex errors?
        """
        self.test_range_validity()
        self.enumerate(self.numbers, self.range[0], lenient)

    def valid(self, lenient=True):
        """Is the given document valid, meaning that `numbers` and
        `range` match?
        """
        if self.bailed:
            return False
        elif self.skip:
            return True
        elif self.enum:
            return self.validity and self.all_exist()
        else:
            try:
                self.enumeration(lenient)
                return self.validity and self.all_exist()
            except ValueError:
                return False


class TapDocumentIterator(object):
    """Iterator over enumerated testcase entries of TAP document.
    Returns None for non-defined testcases. Raises Bailouts.
    """

    def __init__(self, doc):
        self.skip = doc.skip
        self.entries = copy.deepcopy(doc.entries)
        self.enum = TapDocumentValidator(doc).enumeration()
        self.current, self.end = doc.range()

    def __iter__(self):
        return self

    def lookup(self, num):
        """Return testcase for given number or None"""
        try:
            entries_index = self.enum.index(num)
        except ValueError:
            return None

        i = 0
        for entry in self.entries:
            if entry.is_testcase:
                if entries_index == i:
                    entry.number = num
                    return entry
                i += 1
            else:
                raise entry

    def next(self):
        if self.skip:
            raise StopIteration("Document gets skipped")
        if self.current > self.end:
            raise StopIteration("End of entries reached")

        self.current += 1
        return self.lookup(self.current - 1)


class TapDocumentActualIterator(object):
    """Iterator over actual *un*enumerated testcases. Raises Bailouts."""

    def __init__(self, doc):
        self.skip = doc.skip
        self.entries = copy.deepcopy(doc.entries)
        self.current = 0

    def __iter__(self):
        return self

    def next(self):
        if self.skip:
            raise StopIteration("Document gets skipped")
        if self.current >= len(self.entries):
            raise StopIteration("All entries iterated")
        else:
            entry = self.entries[self.current]
            self.current += 1
            if entry.is_testcase:
                return entry
            else:
                raise entry


class TapDocumentFailedIterator(object):
    """Iterate over all failed testcases; the ones that are 'not ok'.
    Numbers stay 'None'. Ignores Bailouts.
    """

    def __init__(self, doc):
        self.current = 0
        self.doc = doc

    def __iter__(self):
        return self

    def next(self):
        if self.doc.skip:
            raise StopIteration("No entries available")
        while True:
            if self.current >= len(self.doc.entries):
                raise StopIteration("All entries iterated")
            else:
                entry = self.doc.entries[self.current]
                self.current += 1
                if entry.is_testcase and not entry.field:
                    return copy.deepcopy(entry)


class TapDocumentTokenizer(object):
    """Lexer for TAP document."""

    # just for documentation
    TOKENS = set(['VERSION_LINE', 'DATA', 'PLAN', 'TESTCASE', 'BAILOUT',
                  'WARN_VERSION_LINE', 'WARN_PLAN', 'WARN_TESTCASE'])

    # regexi to match lines
    VERSION_REGEX = re.compile(r'TAP version (?P<version>\d+)\s*$', flags=re.I)
    PLAN_REGEX = re.compile(
        r'(?P<first>\d+)\.\.(?P<last>\d+)\s*'
        r'(?P<comment>#.*?)?$'
    )
    TESTCASE_REGEX = re.compile((
        r'(?P<field>(not )?ok)'
        r'(\s+(?P<number>\d+))?'
        r'(\s+(?P<description>[^\n]*?)'
        r'(\s+#(?P<directive>(\s+(TODO|SKIP).*?)+?))?)?\s*$'),
        flags=re.IGNORECASE
    )
    BAILOUT_REGEX = re.compile(
        r'Bail out!(?P<comment>.*)',
        flags=re.MULTILINE | re.IGNORECASE
    )

    # lookalike matches
    VERSION_LOOKALIKE = 'tap version'
    PLAN_LOOKALIKE = '1..'
    TESTCASE_LOOKALIKE = ['not ok ', 'ok ']

    def __init__(self):
        self.pipeline = collections.deque()

    @classmethod
    def strip_comment(cls, cmt):
        if cmt is None:
            return u''
        return cmt.lstrip().lstrip('#-').lstrip().rstrip()

    def parse_line(self, line):
        """Parse one line of a TAP file"""
        match1 = self.VERSION_REGEX.match(line)
        match2 = self.PLAN_REGEX.match(line)
        match3 = self.TESTCASE_REGEX.match(line)
        match4 = self.BAILOUT_REGEX.match(line)

        add = lambda *x: self.pipeline.append(x)

        if match1:
            add('VERSION_LINE', int(match1.group('version')))
        elif match2:
            add('PLAN', (match2.group('first'), match2.group('last')),
                self.strip_comment(match2.group('comment')))
        elif match3:
            number = match3.group('number')
            number = int(number) if number else None
            add('TESTCASE', match3.group('field') == 'ok',
                number, self.strip_comment(match3.group('description')),
                match3.group('directive'))
        elif match4:
            add('BAILOUT', match4.group('comment').strip())
        else:
            sline = line.lower().strip()
            lookalike = 'Line "{}" looks like a {}, but does not match syntax'

            if sline.startswith(self.VERSION_LOOKALIKE):
                add('WARN_VERSION_LINE', lookalike.format(sline, 'version line'))
            elif sline.startswith(self.PLAN_LOOKALIKE):
                add('WARN_PLAN', lookalike.format(sline, 'plan'))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[0]):
                add('WARN_TESTCASE', lookalike.format(sline, 'testcase'))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[1]):
                add('WARN_TESTCASE', lookalike.format(sline, 'testcase'))
            else:
                add('DATA', line)

    def from_file(self, filepath):
        """Read TAP file using `filepath` as source."""
        with open(filepath) as fp:
            for line in fp.readlines():
                self.parse_line(line.rstrip('\n\r'))

    def from_string(self, string):
        """Read TAP source code from the given `string`."""
        for line in string.splitlines():
            self.parse_line(line.rstrip('\n\r'))

    def __iter__(self):
        return self

    def next(self):
        try:
            while True:
                return self.pipeline.popleft()
        except IndexError:
            raise StopIteration("All tokens consumed.")


class TapDocumentParser(object):
    """Parser for TAP documents"""

    def __init__(self, tokenizer, lenient=True, logger=None):
        self.tokenizer = tokenizer
        self.lenient_parsing = lenient
        self.doc = None

        if logger:
            self.log = logger
        else:
            logging.basicConfig()
            self.log = logging.getLogger(self.__class__.__name__)

    @classmethod
    def parse_data(cls, lines):
        """Give me some lines and I will parse it as data"""
        data = []
        yaml_mode = False
        yaml_cache = u''

        for line in lines:
            if line.strip() == '---':
                yaml_mode = True
            elif line.strip() == '...':
                data.append(YamlData(yamlish.load(yaml_cache)))
                yaml_cache = u''
                yaml_mode = False
            else:
                if yaml_mode:
                    yaml_cache += line + os.linesep
                else:
                    if len(data) > 0 and isinstance(data[-1], basestring):
                        data[-1] += line + os.linesep
                    else:
                        data.append(line + os.linesep)
        return data

    def warn(self, msg):
        """Raise a warning with text `msg`"""
        if self.lenient_parsing:
            self.log.warn(msg)
        else:
            raise TapParseError(msg)

    def parse(self):
        """Parse the tokens provided by `self.tokenizer`."""
        self.doc = TapDocument()
        state = 0
        plan_written = False
        comment_cache = []

        def flush_cache(comment_cache):
            if comment_cache:
                if self.doc.entries:
                    self.doc.entries[-1].data = self.parse_data(comment_cache)
                else:
                    self.doc.add_header_line(self.parse_data(comment_cache))
                comment_cache = []
            return comment_cache

        for tok in self.tokenizer:
            if tok[0] == 'VERSION_LINE':
                if state != 0:
                    msg = ("Unexpected version line. "
                           "Must only occur as first line.")
                    raise TapParseError(msg)
                self.doc.add_version_line(tok[1])
                state = 1
            elif tok[0] == 'PLAN':
                comment_cache = flush_cache(comment_cache)
                if plan_written:
                    msg = "Plan must not occur twice in one document."
                    raise TapParseError(msg)
                if tok[1][0] > tok[1][1] and not (tok[1] == (1, 0)):
                    self.warn("Plan defines a decreasing range.")

                self.doc.add_plan(tok[1][0], tok[1][1], tok[2], state <= 1)
                state = 2
                plan_written = True
            elif tok[0] == 'TESTCASE':
                comment_cache = flush_cache(comment_cache)

                tc = TapTestcase()
                tc.field = tok[1]
                tc.number = tok[2] if tok[2] else None
                tc.description = tok[3] if tok[3] else None
                tc.directive = tok[4] if tok[4] else None

                self.doc.add_testcase(tc)
                state = 2
            elif tok[0] == 'BAILOUT':
                comment_cache = flush_cache(comment_cache)

                self.doc.add_bailout(TapBailout(tok[1]))
                state = 2
            elif tok[0] == 'DATA':
                comment_cache.append(tok[1])
                state = 2
            elif tok[0] in ['WARN_VERSION_LINE', 'WARN_PLAN', 'WARN_TESTCASE']:
                self.warn(tok[1])
                state = 2
            else:
                raise ValueError("Unknown token: {}".format(tok))

        comment_cache = flush_cache(comment_cache)

    @property
    def document(self):
        if not self.doc:
            self.parse()
        return self.doc


class TapContext(object):
    """A context manager to write TAP files.
    Provides a clean procedural API per document.
    All methods besides `write` and `get` return self;
    thus allowing method chaining.
    """

    def __init__(self, doc=None):
        """Take a `doc` (or create a new one) and provide a context for it"""
        self.doc = doc or TapDocument()
        self.plan_was_written = False
        self.last_element = None

    def plan(self, start=None, end=None, tests=None, comment=None):
        """Define how many tests you want to run.
        Either provide `start` & `end` or `tests` attributes as integers.
        """
        if self.plan_was_written:
            raise RuntimeError("Only one plan per document allowed")

        err_msg = "Provide either `start` and `end` or a number of `tests`"
        if all([v is None for v in [start, end, tests]]):
            raise ValueError(err_msg)
        else:
            if tests is not None:
                start = 1
                end = tests
            elif start is not None and end is not None:
                pass
            else:
                raise ValueError(err_msg)

        self.doc.add_plan(first=start, last=end, skip_comment=comment)
        self.plan_was_written = True
        self.last_element = 'plan'

        return self

    def comment(self, comment):
        """Add a comment at the current position."""
        if self.doc.entries:
            self.doc.entries[-1].data += [comment]
        else:
            self.doc.add_header_line(comment)
        return self

    def _add_tc(self, field, comment, data=None, skip=False, todo=False):
        tc = TapTestcase()
        tc.field = field
        tc.description = comment
        tc.skip = skip
        tc.todo = todo
        if data:
            assert hasattr(data, '__iter__') and not isinstance(data, basestring)
            tc.data += data

        self.doc.add_testcase(tc)

    def ok(self, comment, data=None, skip=False, todo=False):
        """Add information about a succeeded testcase. Always returns True"""
        self._add_tc(True, comment, data, skip, todo)
        self.last_element = 'testcase'
        return self

    def not_ok(self, comment, data=None, skip=False, todo=False):
        """Add information about a failed testcase. Always returns True"""
        self._add_tc(False, comment, data, skip, todo)
        self.last_element = 'testcase'
        return self

    def get(self):
        """Retrieve the document we are working with"""
        return self.doc.copy()

    def bailout(self, comment=u''):
        """Trigger a bailout"""
        self.doc.add_bailout(comment)
        self.last_element = 'bailout'
        return self

    def write(self, stream=sys.stderr):
        """Write the document to stderr"""
        print(unicode(self.doc), file=stream)


def validate(doc):
    """Does TapDocument `doc` represent a successful test run?"""
    validator = TapDocumentValidator(doc)
    return validator.valid()


def repr_harness(doc):
    """Return the conventional representation of perl's TAP::Harness"""
    if not validate(doc):
        count_failed = doc.count_failed()
        count_total = len(doc)
        data = {
            'tests': ', '.join([unicode(f) for f in doc.entries
                                if f.is_testcase and not f.field]),
            'failed': count_failed,
            'count': count_total,
            'perc': 1.0 * count_failed / count_total
        }
        tmpl = (u'FAILED tests {:tests}'
                u'Failed {:failed}/{:count} tests, {perc:0.2f} okay')
        return tmpl.format(**data)
    else:
        return u'All tests successful.'


def tapmerge(*docs):
    """Merge TAP documents provided as argument.
    Performs auto-numbering and returns combined TapDocument.
    Takes maximum TAP document version.
    """
    doc = TapDocument()
    doc.set_version(max([d.metadata['version'] for d in docs]))

    for d in docs:
        doc.metadata['header_comment'] += d.metadata['header_comment']

    number = 1
    modify_numbers = False
    minimum, maximum = float('inf'), 1

    for d in docs:
        for entry in d.entries:
            if entry.is_testcase:
                if entry.number is None:
                    number += 1
                else:
                    number = max(number, entry.number)

            new_entry = entry.copy()
            if modify_numbers:
                new_entry.number = number
            minimum, maximum = min(minimum, new_entry.number), \
                max(maximum, new_entry.number)
            doc.entries.append(new_entry)

        # modify numbers of second documents following
        modify_numbers = True

    skip_comments = [d.metadata['skip_comment'] for d in docs
                     if d.metadata['skip'] and d.metadata['skip_comment']]

    if minimum == float('inf'):
        minimum, maximum = 1, 0

    doc.add_plan(minimum, maximum, '; '.join(skip_comments), all(
        [d.metadata['plan_at_beginning'] for d in docs]
    ))

    return doc


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
