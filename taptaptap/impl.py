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
import codecs
import logging
import yamlish
import collections

__all__ = ['YamlData', 'TapTestcase', 'TapNumbering', 'TapActualNumbering',
           'TapDocument', 'TapDocumentValidator', 'TapDocumentIterator',
           'TapDocumentActualIterator', 'TapDocumentFailedIterator',
           'TapDocumentTokenizer', 'TapDocumentParser', 'TapProtocol',
           'TapWrapper', 'merge']


STR_ENC = 'utf-8'


class YamlData(object):
    """YAML data storage"""
    def __init__(self, data):
        self.data = data

    def __eq__(self, other):
        return self.data == other

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

        key = None
        key_just_set = False
        for val in parts:
            if val.lower() in delimiters:
                key = val.lower()
                if key_just_set:
                    self._directives[key] = u''
                key_just_set = True
            else:
                if key is None:
                    msg = 'Directive must be sequence of TODOs and SKIPs'
                    raise ValueError(msg + ' but is {}'.format(value))
                self._directives[key].append(val)
                key_just_set = False

    @directive.deleter
    def directive(self):
        self._directives = {}

    @property
    def data(self):
        """Annotated data (eg. a backtrace) to the testcase"""
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

    def __eq__(self, other):
        """Test equality"""
        conds = [self.field == other.field, self.number == other.number,
                 self.description == other.description,
                 self.directive == other.directive, self.data == self.data]

        # if one number is None and the other not, it's fine
        is_none = [self.number is None, other.number is None]
        if is_none.count(True) == 1:
            conds[1] = True

        return all(conds)

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
            out += u' # {} '.format(directive)
        out = out.rstrip()
        if self.data:
            data = [unicode(d) for d in self.data]
            out += os.linesep + (os.linesep).join(data)

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
    """An object representing a TAP document. Also acts as context manager."""
    DEFAULT_VERSION = 13

    def __init__(self, version=DEFAULT_VERSION, skip=False):
        # testcases and bailouts
        self.entries = []
        self.metadata = {
            # version line
            'version': version,
            'version_written': False,
            # comment lines before first testcase
            'header_comment': [],
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
            raise ValueError("Header line must only be 1 (!) line")
        line = unicode(line).rstrip() + os.linesep
        self.metadata['header_comment'] += [line]

    def add_plan(self, first, last, skip_comment=u'', at_beginning=True):
        """Add information of a plan like '1..3 # SKIP wip'"""
        self.metadata['plan_at_beginning'] = bool(at_beginning)
        self.metadata['numbering'] = TapNumbering(first=first, last=last)
        if skip_comment:
            self.set_skip(skip_comment)

    def add_testcase(self, tc):
        """Add a ``TapTestcase`` instance `tc` to this document"""
        self.entries.append(tc.copy())

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
                comment = '  # SKIP'
            elif 'skip' not in comment.lower():
                comment = '  # SKIP ' + comment
            else:
                comment = '  # ' + comment.strip()
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

    def count_not_ok(self):
        """How many testcases which are 'not ok' are there?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and not entry.field:
                count += 1
        return count

    def count_ok(self):
        """How many testcases which are 'ok' are there?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.field:
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

        - Requires validation and therefore plan beforehand
        - Returns copy of testcase or None (if range specifies existence)
        - Raises IndexError (if testcase does not exist at all)

        :param num:         Testcase number to look up
        """
        try:
            num = int(num)
        except ValueError:
            raise IndexError('Indexing requires testcase number')

        validator = TapDocumentValidator(self)
        enum = validator.enumeration()
        try:
            index = enum.index(num)
        except ValueError:
            doc_range = self.range()
            if doc_range[0] <= num <= doc_range[1]:
                return None

            msg = "Testcase with number {} does not exist"
            raise IndexError(msg.format(num))

        nr = 0
        for entry in self.entries:
            if entry.is_testcase:
                if nr == index:
                    e = copy.deepcopy(entry)
                    e.number = num
                    return e
                nr += 1

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
                if value is None:
                    self.metadata[key] = None
                else:
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
        self.ctx = TapWrapper(self)
        return self.ctx

    def __exit__(self, exc_type, exc_value, tracebk):
        """Finalize context for this document"""
        self.ctx.finalize()

    def __str__(self):
        """String representation of TAP document"""
        return unicode(self).encode(STR_ENC)

    def __unicode__(self):
        """Unicode representation of TAP document"""
        out = u''
        # version line
        if self.metadata['version_written'] or \
            self.metadata['version'] != self.DEFAULT_VERSION:
            out += u'TAP version {:d}'.format(self.metadata['version'])
            out += os.linesep
        # header comments
        for comment in self.metadata['header_comment']:
            out += unicode(comment)
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
            raise TapMissingPlan("Plan required before document validation")

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
        return '<TapDocumentValidator {} {}{}>'.format(self.numbers,
            self.range, self.enum and ' with enumeration' or '')

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
    Returns None for non-defined testcases.
    Raises Bailouts per default.
    """

    def __init__(self, doc, raise_bailout=True):
        self.skip = doc.skip
        self.entries = copy.deepcopy(doc.entries)
        self.enum = TapDocumentValidator(doc).enumeration()
        self.current, self.end = doc.range()
        self.raise_bailout = raise_bailout

    def __iter__(self):
        return self

    def lookup(self, num):
        """Return testcase for given number or None"""
        try:
            entries_index = self.enum.index(num)
        except ValueError:
            if self.raise_bailout:
                entries_index = -1
            else:
                return None

        i = 0
        for entry in self.entries:
            if entry.is_testcase:
                if entries_index == i:
                    entry.number = num
                    return entry
                i += 1
            elif self.raise_bailout:
                raise entry

        if entries_index == -1:
            return None

    def next(self):
        if self.skip:
            raise StopIteration("Document gets skipped")
        if self.current > self.end:
            raise StopIteration("End of entries reached")

        self.current += 1
        return self.lookup(self.current - 1)


class TapDocumentActualIterator(object):
    """Iterator over actual *un*enumerated testcases. Raises Bailouts."""

    def __init__(self, doc, raise_bailout=True):
        self.skip = doc.skip
        self.entries = copy.deepcopy(doc.entries)
        self.current = 0
        self.raise_bailout = raise_bailout

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
            elif self.raise_bailout:
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
        self.last_indentation = 0

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
            self.last_indentation = None
        elif match2:
            add('PLAN', (int(match2.group('first')), int(match2.group('last'))),
                self.strip_comment(match2.group('comment')))
            self.last_indentation = None
        elif match3:
            number = match3.group('number')
            number = int(number) if number else None
            add('TESTCASE', match3.group('field').lower() == 'ok',
                number, self.strip_comment(match3.group('description')),
                match3.group('directive'))
            self.last_indentation = 0
        elif match4:
            add('BAILOUT', match4.group('comment').strip())
            self.last_indentation = None
        else:
            sline = line.lower().strip()
            lookalike = 'Line "{}" looks like a {}, but does not match syntax'

            if sline.startswith(self.VERSION_LOOKALIKE):
                add('WARN_VERSION_LINE', lookalike.format(sline, 'version line'))
            elif sline.startswith(self.PLAN_LOOKALIKE):
                add('WARN_PLAN', lookalike.format(sline, 'plan'))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[0]):
                add('WARN_TESTCASE', lookalike.format(sline, 'test line'))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[1]):
                add('WARN_TESTCASE', lookalike.format(sline, 'test line'))

            add('DATA', line)

    def from_file(self, filepath, encoding='utf-8'):
        """Read TAP file using `filepath` as source."""
        with codecs.open(filepath, encoding=encoding) as fp:
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
                    line = line.rstrip('\r\n')
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
                    self.doc.entries[-1].data += self.parse_data(comment_cache)
                else:
                    for line in self.parse_data(comment_cache):
                        self.doc.metadata['header_comment'] += [line]
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


class TapProtocol:
    def __init__(self, version=TapDocument.DEFAULT_VERSION):
        return NotImplemented

    def plan(self, first, last, skip=u''):
        raise NotImplementedError()

    def testcase(self, ok, description=u'', skip=u'', todo=u''):
        raise NotImplementedError()

    def bailout(self, comment):
        raise NotImplementedError()

    def write(self, line):
        raise NotImplementedError()

    def finalize(self):
        return NotImplemented


class TapWrapper(object, TapProtocol):
    """One of the nice TAP APIs. See ``api`` module for others.

    Wraps a `TapDocument` and provides the nicer `TapProtocol` API.
    All methods besides `write` and `get` return self;
    thus allowing method chaining. `plan` can be called at any time
    unlike the TAP file format specification defines.
    """

    def __init__(self, doc=None, version=TapDocument.DEFAULT_VERSION):
        """Take a `doc` (or create a new one)"""
        self.doc = doc or TapDocument(version)
        self._plan = None

    def plan(self, first=None, last=None, skip=u'', tests=None):
        """Define how many tests are run. Either provide `first` & `last`
        or `tests` as integer attributes. `skip` is an optional message.
        If set, the test run was skipped because of the reason given by `skip`.
        """
        if self._plan is not None:
            raise RuntimeError("Only one plan per document allowed")

        err_msg = "Provide either first and last params or tests param"
        if all([v is None for v in [first, last, tests]]):
            raise ValueError(err_msg)
        else:
            if tests is not None:
                first = 1
                last = tests
            elif first is not None and last is not None:
                pass
            else:
                raise ValueError(err_msg)

        self._plan = (first, last, skip)
        return self

    def write(self, line):
        """Add a comment `line` at the current position."""
        if self.doc.entries:
            self.doc.entries[-1].data += [line]
        else:
            self.doc.add_header_line(line)
        return self

    def testcase(self, ok=True, description=u'', skip=False, todo=False):
        """Add a testcase entry to the TapDocument"""
        tc = TapTestcase()
        tc.field = ok
        tc.description = description
        if skip:
            tc.skip = skip
        if todo:
            tc.todo = todo

        self.doc.add_testcase(tc)
        return self

    def ok(self, description=u'', skip=False, todo=False):
        """Add a succeeded testcase entry to the TapDocument"""
        self.testcase(True, description, skip, todo)
        return self

    def not_ok(self, description=u'', skip=False, todo=False):
        """Add a failed testcase entry to the TapDocument"""
        self.testcase(False, description, skip, todo)
        return self

    def unwrap(self):
        """Retrieve a copy of the current document"""
        self.finalize()
        return self.doc.copy()

    def bailout(self, comment=u''):
        """Trigger a bailout"""
        self.doc.add_bailout(comment)
        return self

    def out(self, stream=sys.stderr):
        """Write the document to stderr. Requires finalization."""
        self.finalize()
        print(unicode(self.doc), file=stream)

    def finalize(self):
        """Finalize document. Just checks whether plan has been written.
        Any operation afterwards besides `out` and `unwrap` is
        undefined behavior.
        """
        if not self._plan:
            raise TapMissingPlan("Cannot finalize document. Plan required.")
        self.doc.add_plan(first=self._plan[0], last=self._plan[1],
                          skip_comment=self._plan[2])
        return self

    def __str__(self):
        return unicode(self.doc).encode(STR_ENC)

    def __unicode__(self):
        return unicode(self.doc)


def merge(*docs):
    """Merge TAP documents provided as argument.
    Takes maximum TAP document version. Testcase numbers are
    incremented by consecutive offsets based on the TAP plan.
    """
    # this is a incredible complex algorithm, just sayin'
    if not docs:
        return None

    doc = TapDocument()
    doc.set_version(max([d.metadata['version'] for d in docs]))

    for d in docs:
        if d.metadata['header_comment']:
            comments = [c for c in d.metadata['header_comment'] if c.strip()]
            doc.metadata['header_comment'] += comments

    # normalize ranges
    ranges, offset = [], 1
    minimum, maximum, count = float('inf'), 0, 0
    for d in docs:
        r = list(d.range())
        r[1] = max(r[1], r[0] + len(d) - 1)
        r = map(lambda x: x + offset - r[0], r)
        offset = r[1] + 1
        ranges.append(tuple(r))

    for d_id, d in enumerate(docs):
        # create copies and assign normalized numbers
        numbers, count_assignments = [], 0
        for entry in d.entries:
            c = entry.copy()
            if entry.is_testcase:
                if c.number is not None:
                    c.number -= d.range()[0]
                    c.number += ranges[d_id][0]
                numbers.append(c.number)
            doc.entries.append(c)
            count_assignments += 1

        # use `enumerate` to compute assignments
        enums = TapDocumentValidator.enumerate(numbers, first=ranges[d_id][0])
        if enums:
            minimum = min(minimum, min(enums))
            maximum = max(maximum, max(enums))
        # assign numbers
        index = 0
        for entry in doc.entries[-count_assignments or len(doc.entries):]:
            if not entry.is_testcase:
                continue
            number = enums[index]
            entry.number = number
            minimum, maximum = min(minimum, number), max(maximum, number)
            index += 1
            count += 1

    skip_comments = []
    for d in docs:
        if d.metadata['skip'] and d.metadata['skip_comment']:
            skip_comments.append(d.metadata['skip_comment'])

    pab = any([d.metadata['plan_at_beginning'] for d in docs])

    if count == 0:
        minimum, maximum = 1, 0
    elif minimum == float('inf'):
        minimum, maximum = 1, count
    else:
        maximum = max(maximum, minimum + count - 1)

    doc.add_plan(minimum, maximum, '; '.join(skip_comments), pab)

    return doc
