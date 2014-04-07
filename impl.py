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

import io
import re
import os
import sys
import copy
import locale
import logging
import yamlish
import collections

__all__ = ['YamlData', 'TapTestcase', 'TapActualNumbering', 'TapNumbering',
           'TapDocument', 'TapDocumentIterator', 'TapDocumentActualIterator',
           'TapDocumentFailedIterator', 'TapDocumentTokenizer',
           'TapDocumentParser', 'TapStream', 'TapContext', 'validate',
           'repr_harness', 'tapmerge', 'parse_file', 'parse_string']


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

    def __init__(self):
        # test line
        self._field = None
        self._number = None
        self.description = u''
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
        out = u'ok ' if self.field else u'not ok '
        if self.number is not None:
            out += unicode(self.number) + u' '
        if self.description:
            out += u'- {} '.format(self.description)
        if self.directive is not None:
            out += u'# {} '.format(self.directive)
        if self.data:
            data = [unicode(d) for d in self.data]
            out += os.linesep + self.indent((os.linesep).join(data), 2)
        return out

    def __str__(self):
        return unicode(self).encode(STR_ENC)


class TapActualNumbering(object):
    """TAP testcase numbering. In TAP documents it is called 'the plan'."""

    def __init__(self, num_range=(1, 0), numbers=None):
        """Constructor.

        :param tuple num_range:   (first, last) testcase numbers
        :param list numbers:      list of testcase numbers (possibly Nones)
        """
        self.init_range(first=num_range[0], last=num_range[1])
        self.init_numbering(copy.deepcopy(numbers or []))

    def init_numbering(self, numbers):
        """Initialize numbering (is a list of numbers and Nones)."""
        self.numbers = list(numbers)
        return self

    def init_range(self, first=None, last=None, tests=None, strict=False):
        """Provide `first` and `last` XOR a number of `tests`.

        `first` and `last` are testcase numbers. Both inclusive.

        If `strict` is True, a decreasing range (except '1..0')
        will raise a TapInvalidNumbering Exception.
        Otherwise it will just be normalized (set `last` to `first`).
        """
        if first is not None and last is not None:
            self.first = int(first)
            self.length = int(last) - int(first) + 1

            if int(last) == 0 and int(first) == 1:
                self.length = 0
            elif int(last) < int(first):
                self.length = 0
                if strict:
                    msg = 'range {}..{} is decreasing'.format(first, last)
                    msg = 'Invalid testcase numbering: ' + msg
                    raise TapInvalidNumbering(msg)

        elif tests is not None:
            self.first = 1
            self.length = int(tests)

        else:
            msg = 'Either provide a first and last or a number of tests'
            raise ValueError(msg)

        assert(self.first >= 0 and self.length >= 0)
        return self

    @staticmethod
    def enumerate(numbers, first=1, lenient=False):
        """Take a sequence of positive numbers and assign numbers,
        where None is given.

            >>> enumerate([1, 2, None, 4])
            [1, 2, 3, 4]
            >>> enumerate([None, None, 2])
            Traceback (most recent call last):
              File "<stdin>", line 1, in <module>
            IndexError: Testcase number 2 was already used
            >>> enumerate([None, None, 2], lenient=True)
            [1, 3, 2]

        post conditions:
        * Always the smallest possible integers are used (starting with `first`).
          But if a high integer is given, this one is used for continuation.
        * `enumerate` returns a sequence of positive numbers or
          raises an IndexError.
        * If `numbers` uses a number twice, even lenient=True throws an error.
        """
        assigned = set()
        fixed = set()
        sequence = []
        next_number = 1

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
                if nr < 0:
                    raise ValueError("Testcase number must be non-negative")
                if nr in fixed:
                    raise IndexError(reuse_errmsg.format(nr))
                elif nr in assigned:
                    if not lenient:
                        raise IndexError(reuse_errmsg.format(nr))
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

    def __len__(self):
        return self.length

    def __nonzero__(self):
        return True

    def __contains__(self, tc_number):
        """Is `tc_number` within this TapNumbering range?"""
        tc_number = int(tc_number)
        if self.length == 0:
            return False
        else:
            return self.first <= tc_number < self.first + self.length

    def get_enumeration(self, lenient=True):
        """Get enumeration for given `self.numbers`. Enumeration is the list
        of testcase numbers like `self.numbers` but with Nones eliminated.

        :param bool lenient:    Shall I fix simple errors myself?
        """
        return self.enumerate(self.numbers, first=self.first, lenient=lenient)

    def inc(self):
        """Increase numbering for one new testcase"""
        self.length += 1

    def normalized_plan(self):
        """Return a normalized plan where first=1"""
        return '{:d}..{:d}'.format(1, self.length)

    def range(self):
        """Get range of this numbering: (min, max)"""
        return (self.first, self.first + self.length - 1)

    def __iter__(self):
        return iter(range(self.first, self.first + self.length))

    def __unicode__(self):
        """Return unicode representation of plan.
        If it was initially a decreasing range, first=last now.
        """
        return '{:d}..{:d}'.format(self.first, self.first + self.length - 1)

    def matches(self):
        """Can `self.numbers` match `self.first` and `self.last`?"""
        try:
            if len(self.numbers) != self.length:
                return False
            enums = self.get_enumeration(lenient=True)
            if not enums:
                return True
            last = self.first + self.length - 1
            if min(enums) != self.first or max(enums) != last:
                return False
            return True
        except IndexError:
            return False


class TapNumbering(list):
    pass


class TapDocument(object):
    """An object representing a TAP document"""
    DEFAULT_VERSION = 13

    def __init__(self, version=DEFAULT_VERSION, skip=False):
        self.entries = []
        self.metadata = {
            # data of first line
            'version': version,
            # possibly 2+ lines
            'header_comment': u'',
            # numbering objects
            'actual_numbering': None,
            'numbering': TapNumbering(),
            # data of plan
            'range': (1, 0),
            'plan_at_beginning': True,
            'skip': skip,
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
        self.metadata['skip'] = True
        self.metadata['skip_comment'] = skip_comment

    def add_version_line(self, version=DEFAULT_VERSION):
        """Add information of version lines like 'TAP version 13'"""
        self.set_version(version)

    def add_header_line(self, line):
        """Add header comment line for TAP document"""
        self.metadata['header_comment'] += unicode(line).rstrip()
        self.metadata['header_comment'] += os.linesep

    def add_plan(self, first, last, skip_comment=u'', at_beginning=True):
        """Add information of a plan like '1..3 # SKIP wip'"""
        self.metadata['range'] = (first, last)
        self.metadata['plan_at_beginning'] = bool(at_beginning)
        self.metadata['actual_numbering'] = None
        if skip_comment:
            self.set_skip(skip_comment)

    def add_testcase(self, tc):
        """Add a ``TapTestcase`` or ``TapBailout`` instance `tc`"""
        self.metadata['numbering'].append(tc.number)
        self.metadata['actual_numbering'] = None
        self.entries.append(copy.deepcopy(tc))

    def add_bailout(self, bo):
        """Add a ``TapBailout`` instance `bo` to this document"""
        self.metadata['actual_numbering'] = None
        self.entries.append(bo.copy())

    # processing

    def _get_actual_numbering(self):
        """Compute the actual numbering"""
        if self.metadata['actual_numbering']:
            return  # already there
        if 'range' not in self.metadata:
            raise TapMissingPlan('Plan required before generation of numbering')

        self.metadata['actual_numbering'] = TapActualNumbering(
            self.metadata['range'],
            self.metadata['numbering']
        )

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
        self._get_actual_numbering()
        return len(self.metadata['actual_numbering'])

    def actual_length(self):
        """Return actual number of testcases in this document"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase:
                count += 1
        return count

    def range(self):
        """Get range like ``(1, 2)`` for this document"""
        self._get_actual_numbering()
        return self.metadata['actual_numbering'].range()

    def actual_range(self):
        """Get actual range"""
        return (1, self.actual_length())

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

    def __contains__(self, tc_id):
        """Does this document contain a testcase with id `tc_id`?"""
        self._get_actual_numbering()
        return tc_id in self.metadata['actual_numbering']

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

    def range_matches(self):
        """Does the plan correspond to the stored testcases?"""
        self._get_actual_numbering()
        return self.metadata['actual_numbering'].matches()

    def valid(self):
        """Is this document valid?"""
        return validate(self)

    def __getitem__(self, num):
        self._get_actual_numbering()
        enum = self.metadata['actual_numbering'].get_enumeration()
        return copy.deepcopy(self.entries[enum[num]])

    def __iter__(self):
        """Get iterator for testcases"""
        return TapDocumentIterator(self)

    def __getstate__(self):
        """Return state of this object"""
        state = copy.copy(self.metadata)
        state['entries'] = [entry.__getstate__() for entry in self.entries]
        return state

    def __setstate__(self, state):
        """Restore object's state from `state`"""
        self.entries = []
        self.metadata = {}

        for key, value in state.iteritems():
            if key == 'entries':
                for entry in value:
                    tc = TapTestcase()
                    tc.__setstate__(entry)
                    self.entries.append(tc)
            else:
                self.metadata[key] = value

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
        # version line
        out = u'TAP version {:d}{}'.format(self.metadata['version'], os.linesep)
        # header comments
        out += self.metadata['header_comment']
        # [possibly] plan
        out += self.plan() if self.metadata['plan_at_beginning'] else u''
        # testcases and bailouts
        for entry in self.entries:
            out += unicode(entry)
        # [possibly] plan
        out += self.plan() if not self.metadata['plan_at_beginning'] else u''

        return out


class TapDocumentIterator(object):
    """Iterator over testcases. Ignores Bailouts."""
    def __init__(self, doc):
        self.current = 0
        self.doc = doc

    def __iter__(self):
        return self

    def next(self):
        if self.doc.skip:
            raise StopIteration("No entries available")
        if self.current >= len(self.doc.entries):
            raise StopIteration("All entries iterated")
        else:
            self.current += 1
            return copy.deepcopy(self.doc.entries[self.current])


class TapDocumentActualIterator(object):
    """Iterator over actual testcase entries of TAP document.
    Terminates either with TapBailout or StopIteration.
    Bailout is raised at the end of document; *NOT* the correct index.
    Returns None for non-defined testcases.
    """
    def __init__(self, doc):
        self.range = doc.actual_range()
        self.current = self.range[0]
        self.bailed = doc.bailed()
        self.bailout_message = doc.bailout_message()
        self.doc = doc

    def __iter__(self):
        return self

    def next(self):
        if self.doc.skip:
            raise StopIteration("No entries available")
        if self.current > self.range[1]:
            if self.bailed:
                raise TapBailout(self.bailout_message)
            else:
                raise StopIteration("All entries iterated")
        else:
            self.current += 1
            try:
                return self.doc[self.current]
            except IndexError:
                return None


class TapDocumentFailedIterator(object):
    """Iterate over all failed testcases; the ones that are 'not ok'.
    Ignores Bailouts.
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
            self.current += 1
            if self.current >= len(self.doc.entries):
                raise StopIteration("All entries iterated")
            else:
                tc = self.doc.entries[self.current]
                if tc.is_testcase and not tc.field:
                    return copy.deepcopy(self.doc.entries[self.current])


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
        r'(\s+(?P<number>\d+)'
        r'(\s+(?P<description>[^\n]*?)'
        r'(\s+#(?P<directive>(\s+(TODO|SKIP).*?)+?))?)?)?\s*$'),
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
        match4 = self.BAILOUT_REGEX(line)

        add = lambda *x: self.pipeline.append(x)

        if match1:
            add('VERSION_LINE', int(match1.group('version')))
        elif match2:
            add('PLAN', (match2.group('first'), match2.group('last')),
                self.strip_comment(match2.group('comment')))
        elif match3:
            add('TESTCASE', match3.group('field') == 'ok',
                int(match3.group('number')),
                self.strip_comment(match3.group('description')),
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
                yield self.pipeline.popleft()
        except IndexError:
            # All tokens consumed.
            pass


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
                data.append(yamlish.load(yaml_cache))
                yaml_cache = u''
                yaml_mode = False
            else:
                if yaml_mode:
                    yaml_cache += line
                else:
                    if len(data) > 0 and isinstance(data[-1], basestring):
                        data[-1] += line
                    else:
                        data.append(line)
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

                self.doc.add_plan(tok[1][0], tok[1][1], tok[2], state == 1)
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


class TapStream(io.TextIOBase):
    """A stream object to read. Conforms to `Text I/O`_
    (even though Text I/O was designed for py3k).

    .. _`Text I/O`: http://legacy.python.org/dev/peps/pep-3116/#text-i-o
    """

    def __init__(self, buf, encoding=None, errors=None,
                 newline=None, line_buffering=False):
        super(TapStream, self).__init__(self, buf, encoding, errors,
                                        newline, line_buffering)
        self.doc = None
        self.tokenizer = TapDocumentTokenizer()

        self.lenient = True
        self.buf = u''

        # {'version', 'plan', 'bailout', 'testcase'} (or any subset)
        self.write_mode = set(['plan', 'testcase', 'version', 'bailout'])
        self.bailout_was_last = False

    def __enter__(self):
        """Return context for this stream"""
        return TapContext(self.doc)

    def __exit__(self, exc_type, exc_value, tracebk):
        """Finalize context for this document"""
        pass

    def read(self, n=-1):
        """Read and return at most `n` characters from the stream
        as a single `unicode`. If `n` is negative or None, reads until EOF."""
        self.flush()
        representation = unicode(self.doc)
        if n == -1 or n is None:
            #self.seek(0, io.SEEK_END)
            return representation[self.tell():]
        else:
            sliced = representation[self.tell():self.tell() + n]
            self.seek(self.tell() + n, io.SEEK_SET)
            return sliced

    def write(self, b=''):
        """Returns number of bytes written, which may be ``< len(b)``."""
        enc = self.encoding or locale.getpreferredencoding()
        string = b.decode(enc, errors='strict')
        self.doc = None

        if os.linesep in b:
            # consume all but the last line
            lines = self.buf.splitlines()
            self.buf = lines[-1]
            for line in lines[:-1]:
                self.tokenizer.parse_line(line)
        else:
            self.buf += string
        return len(b)

    def seek(self, offset, whence=io.SEEK_SET):
        """Change the stream position to the given byte offset."""


    def truncate(self, pos=None):
        raise NotImplementedError("Truncating is unsupported by TapStream")
        #return int

    def readline(self, limit=-1):
        """Read and return one line from the stream. If `limit` is specified,
        at most `limit` bytes will be read.

        The newlines argument to open() can be used to select
        the line terminator(s) recognized.
        """
        self.flush()
        representation = unicode(self.doc)
        cur = self.tell()
        newline_index = representation.find(self.newline or '\n', cur)

        if limit != -1:
            newline_index = min(newline_index, cur + limit)

        if newline_index == -1:
            sliced = representation[cur:]
            if limit != -1 and len(sliced) > cur + limit:
                self.seek(cur + limit, io.SEEK_SET)
                return sliced[0:limit]
            else:
                self.seek(0, io.SEEK_END)
                return sliced
        else:
            self.seek(newline_index, io.SEEK_SET)
            return representation[cur:newline_index]

    def next(self):
        """Same as `readline()` except raises ``StopIteration``
        if EOF hit immediately.
        """
        try:
            return self.readline()
        except IndexError:
            raise StopIteration('End of stream reached')

    def flush(self):
        """Finalize `self.doc` using `self.tokenizer`"""
        if not self.doc:
            for line in self.buf.splitlines():
                self.tokenizer.parse_line(line)
            self.buf = u''
            parser = TapDocumentParser(self.tokenizer, self.lenient)
            self.doc = parser.document

    def __iter__(self):
        """Returns an iterator that returns lines from the file
        (which happens to be ``self``).
        """
        return iter(unicode(self.doc))


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

        self.doc.add_plan(start, end, comment)
        self.plan_was_written = True
        self.last_element = 'plan'

        return self

    def comment(self, comment):
        """Add a comment at the current position."""
        if self.doc.entries:
            self.doc.entries[-1].append_data(comment)
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
    if doc.skip:
        return True
    if doc.bailed():
        return False
    if not doc.range_matches():
        return False

    for entry in TapDocumentActualIterator(doc):
        if entry is None or not entry.field:
            return False

    return True


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
    """Parse a TAP file and return its testrun success.

    :param unicode filepath:    A valid filepath for `open`
    :param bool lenient:        Lenient parsing? If so errors are thrown late.
    :return bool status:        Does this file describe a successful testrun?
    """
    tokenizer = TapDocumentTokenizer()
    tokenizer.from_file(filepath)
    parser = TapDocumentParser(tokenizer, lenient)
    doc = parser.document
    return validate(doc)


def parse_string(string, lenient=True):
    """Parse the given `string` and return its testrun success.

    :param unicode string:      A string to parse
    :param bool lenient:        Lenient parsing? If so errors are thrown late.
    :return bool status:        Does this file describe a successful testrun?
    """
    tokenizer = TapDocumentTokenizer()
    tokenizer.from_string(string)
    parser = TapDocumentParser(tokenizer, lenient)
    doc = parser.document
    return validate(doc)
