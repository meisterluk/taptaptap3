#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    impl.py
    ~~~~~~~

    TAP file handling implementation.

    (c) BSD 3-clause.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

from .exc import TapParseError, TapBailout, TapInvalidNumbering

import io
import re
import os
import sys
import locale
import codecs
import logging
import yamlish

__all__ = ['TapDocumentReader', 'TapParseError', 'TapBailout', 'TapTestcase',
           'TapDocumentIterator', 'TapDocument', 'TapDocumentReader',
           'TapNumbering', 'parse_string', 'parse_file']


class TapTestcase(object):
    """Object representation of an entry in a TAP file"""
    is_testcase = True
    is_bailout = False

    def __init__(self):
        # test line
        self._field = None
        self._number = None
        self.description = None
        self._directives = {'skip': [], 'todo': []}
        # data
        self._data = None

    @staticmethod
    def indent(text, indent=2):
        """Indent all lines of ``text`` by ``indent`` spaces"""
        return re.sub('(^|\n)', '\\1' + (' ' * indent), text)

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
        """A TAP directive like '# TODO work in progress'"""
        out = u''
        for skip_msg in self._directives['skip']:
            out += u'SKIP {} '.format(skip_msg)
        for todo_msg in self._directives['todo']:
            out += u'TODO {} '.format(todo_msg)
        return out and out[:-1] or u''

    @directive.setter
    def directive(self, value):
        if value is None:
            self._directives['skip'] = []
            self._directives['todo'] = []
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
        return self._data

    @data.setter
    def data(self, value):
        if not isinstance(value, basestring):
            self._data = value
            return

        match1 = re.match('(^|{})((not )?ok)'.format(os.linesep), value)
        if match1:
            msg = "'{}' must not occur in data attribute"
            raise ValueError(msg.format(match1.group(2)))

        match2 = re.match('(^|{})((\d+)\.\.(\d+))'.format(os.linesep), value)
        if match2:
            msg = "Plan '{}' must not occur in data attribute"
            raise ValueError(msg.format(match2.group(2)))

        self._data = value

    # TODO: attach additional data

    @data.deleter
    def data(self):
        self._data = None

    @property
    def todo(self):
        """Is a TODO flag annotated to this testcase?"""
        return bool(self._directives['todo'])

    @todo.setter
    def todo(self, what):
        """Add a TODO flag to this testcase"""
        if what:
            self._directives['todo'].append(what)

    @property
    def skip(self):
        """Is a SKIP flag annotated to this testcase?"""
        return bool(self._directives['skip'])

    @skip.setter
    def skip(self, what):
        """Add a SKIP flag to this testcase"""
        if what:
            self._directives['skip'].append(what)

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
        self.directives = obj['directives']
        self.data = obj['data']

    def __repr__(self):
        """Representation of this object"""
        field = self.field and 'ok' or 'not ok'
        num = self.number and ' #{}'.format(self._number) or ''
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
        out = u''
        out += self.field and 'ok ' or 'not ok '
        if self.number is not None:
            out += unicode(self.number) + ' '
        if self.description:
            out += '- ' + unicode(self.description) + ' '
        if self.directive is not None:
            out += self.directive + ' '
        if self.data is not None:
            if isinstance(self.data, basestring):
                data = unicode(os.linesep) + self.data
            else:
                data = unicode(os.linesep)
                for element in self.data:
                    if isinstance(element, basestring):
                        data += element
                    else:
                        data += self.indent(yamlish.dumps(element), 2)

            out = out[:-1] + data
        return out

    def __str__(self):
        return unicode(self).encode(sys.getdefaultencoding())


class TapDocumentIterator(object):
    def __init__(self, tcs):
        self.current = 0
        self.tcs = tcs or []
        self.bailout = None
        self.bailout_index = None

    def add_bailout(self, bailout_obj, index):
        """Add a TapBailout instance as bailout"""
        assert bailout_obj, "Bailout object must not be TapBailout instance"
        self.bailout = bailout_obj
        self.bailout_index = index

    def __iter__(self):
        return self

    def next(self):
        if self.bailout and self.current == self.bailout_index:
            raise self.bailout
        if self.current >= len(self.tcs):
            raise StopIteration
        else:
            self.current += 1
            return self.tcs[self.current]

class TapNumbering(object):
    """TAP testcase numbering. In TAP documents it is called "the plan".
    Only to be used by `TapDocument` internally.
    """

    PLAN_REGEX = re.compile(r'(?P<plan>(\d+)\.\.(\d+))', flags=re.IGNORECASE)

    def __init__(self, first=None, last=None, tests=None, strict=False):
        """Constructor. Provide `first` and `last` XOR a number of `tests`.

        `first` and `last` are testcase numbers. Both inclusive.

        If `strict` is True, a decreasing range will raise a TapInvalidNumbering
        Exception. Otherwise it will just be normalized (set `last` to `first`).
        """
        if first is not None and last is not None:
            self.first = int(first)
            self.length = int(last) - int(first) + 1

            if int(last) < int(first):
                if strict:
                    msg = 'range {}..{} is decreasing'.format(first, last)
                    raise TapInvalidNumbering('Invalid testcase numbering: ' + msg)
                else:
                    self.length = 0

        elif tests is not None:
            self.first = 1
            self.length = int(tests)
        else:
            msg = 'Either provide a first and last or a number of tests'
            raise ValueError(msg)

        assert(self.first >= 0 and self.length >= 0)

    def __len__(self):
        return self.length

    def __contains__(self, tc_number):
        """Is `tc_number` within this TapNumbering range?"""
        tc_number = int(tc_number)
        if self.length == 0:
            return False
        else:
            return self.first <= tc_number < self.first + self.length

    @classmethod
    def parse(cls, string, strict=False):
        """Parse the `string` specifying a plan. See constructor
        for `strict` documentation. Returns a new TapNumbering instance.
        """
        string = string.rstrip()
        match = cls.PLAN_REGEX.match(string)
        if match:
            if len(match.group(0)) != len(string):
                raise ValueError("Trailing text in plan '{}'".format(string))
            return TapNumbering(first=match.group(2),
                last=match.group(3), strict=strict)
        else:
            msg = "String '{}' does not specify plan"
            raise ValueError(msg.format(string))

    def inc(self):
        """Increase numbering for one new testcase"""
        self.length += 1

    def normalized_plan(self):
        """Return a normalized plan where first=1"""
        if self.length == 0:
            raise ValueError("Cannot create plan for 0 testcases")
        return '{:d}..{:d}'.format(1, self.length)

    def __iter__(self):
        return iter(range(self.first, self.first + self.length))

    def __unicode__(self):
        """Return unicode representation of plan.
        If it was initially a decreasing range, first=last now.
        """
        if self.length == 0:
            raise ValueError("Cannot create plan for 0 testcases")
        return '{:d}..{:d}'.format(self.first, self.first + self.length - 1)


class TapDocument(TapNumbering):
    """An object representing a whole TAP document"""

    def __init__(self, version=13, skip=False):
        # TAP version *
        self.version = int(version)
        # comment before first testcase
        # TODO: implementation
        self.header_comment = ''
        # sequence of testcases in document
        self.testcases = []
        # TAP plan
        self.range = None
        # Bail out!
        self.bailout = None
        self.bailout_index = None
        # Testcase is flagged to be skipped
        self.skip = skip

    def __len__(self):
        """Return number of testcases"""
        return len(self.testcases)

    def __nonzero__(self):
        return True

    def get_actual_range(self):
        """Get the actual range of the associated testcases.

        :return:        (minimum number, maximum number)
        """
        if not self.testcases:
            minimum = 1
            maximum = 0
        else:
            current, last, minimum, maximum = None, None, None, None
            for tc in self.testcases:
                if tc.number is None and last is not None:
                    current = last + 1
                elif tc.number is None and last is None:
                    current = 1
                else:
                    current = tc.number

                assert current is not None
                if minimum is None or current < minimum:
                    minimum = current
                if maximum is None or current > maximum:
                    maximum = current
                last = current

        return (minimum, maximum)

    def _create_plan(self, limits, comment):
        plan = u'{:d}..{:d}'.format(limits[0], limits[1])

        is_12 = self.version == 12
        if is_12 and not self.testcases and 'skip' not in comment.lower():
            comment = comment and (u'SKIP ' + comment) or u'SKIP'

        if comment:
            plan += u' # {}'.format(comment)

        return plan

    def get_actual_plan(self, comment=u''):
        """Get the plan of this TAP document in unicode representation.
        Actual here means that the testcase numbers are used
        instead of the range that was probably added via `add_range`.
        """
        if os.linesep in comment:
            raise ValueError('Comment must not contain newline')

        limits = self.get_actual_range()
        return self._create_plan(limits, comment)

    def add_range(self, minimum, maximum, overwrite=False):
        """Add a range of the testcases as specified in a plan.
        Set `overwrite` to True, if you want to overwrite previous ranges.
        """
        if not overwrite and self.range:
            raise RuntimeError('Plan already got specified')

        minimum, maximum = (int(minimum), int(maximum))
        if minimum < 0 or maximum < 0:
            raise ValueError('Range elements must be positive')
        self.range = (minimum, maximum)

    def get_plan_range(self):
        """Get the minimum and maximum number of the testcases"""
        if self.range:
            return self.range
        else:
            return self.get_actual_range()

    def get_plan(self, comment=u''):
        """Get the plan of this TAP document in unicode representation.
        Either using the data added by `add_range` or call to `get_actual_plan`
        """
        return self._create_plan(self.get_plan_range(), comment)

    def _range_matches(self):
        """Are all specified testcases (of the plan) 'ok' (and do exist)?
        Returns False, iff
          * not all testcases in the plan, do exist and are 'ok' or skipped
          * the number of TCs in the plan correspond to the number of TCs
          * one testcase does not specify a testcase number
        """
        if self.range:
            limits = self.range
        else:
            limits = self.get_actual_range()
        assert limits[0] >= 0 and limits[1] >= 0

        elements = range(limits[0], limits[1] + 1)
        for tc in self.testcases:
            try:
                elements.remove(tc.number)
                if not tc.field and not tc.skip:
                    return False
            except ValueError:
                return False

        return len(elements) == 0

    @staticmethod
    def _enumerate(testcases):
        """Take a set of testcases and return map {testcase: number}"""
        result = {}
        used_numbers = set()
        number = 1

        REUSE_ERROR = "Testcase number {} was already used"
        for tc in testcases:
            if tc.number is None:
                if number in used_numbers:
                    raise IndexError(REUSE_ERROR.format(number))
                result[tc] = number
                used_numbers.add(number)
                number += 1
            else:
                nr = int(tc.number)
                if nr in used_numbers:
                    raise IndexError(REUSE_ERROR.format(nr))
                result[tc] = nr
                used_numbers.add(nr)
                number = nr + 1

        return result

    def add_testcase(self, tc):
        """Add a `TapTestcase` object to this document"""
        self.testcases.append(tc)

    def add_bailout(self, comment=u''):
        """Add a bailout at the current state of testcases"""
        if os.linesep in comment:
            raise ValueError('Comment must not contain newline')

        self.bailout = TapBailout(comment)
        self.bailout_index = len(self.testcases)

    def remove_testcase(self, tc):
        """Remove a `TapTestcase` object from the list of testcases"""
        self.testcases.remove(tc)

    def count_failed(self):
        """Count the number of testcases which reported 'not ok' as result."""
        return len(filter(lambda tc: not tc.field, self.testcases))

    def count_todo(self):
        """Count the number of testcases with a TODO flag"""
        return len(filter(lambda tc: tc.todo, self.testcases))

    def count_skip(self):
        """Count the number of testcases with a SKIP flag"""
        return len(filter(lambda tc: tc.skip, self.testcases))

    def renumber(self):
        """Lose all numbers in testcases (and plan) and set them to '1..N'"""
        for num, tc in enumerate(self.testcases):
            tc.number = num + 1
        self.range = None

    def auto_enumerate(self):
        """Assign numbers to testcases with `number` *None*::

            [1, 2, None, 4] will become [1, 2, 3, 4]
            [1, 2, None, 5] will become [1, 2, 3, 5]
            [1, 3, None, 8] will become [1, 3, 4, 8]
            [1, 3, None, 2] will become [1, 3, 4, 2]
            [1, 3, None, 4] will throw an IndexError
            [1, 3, None, 3] will throw an IndexError
        """
        assignment = self._enumerate(self.testcases)
        for tc in self.testcases:
            tc.number = assignment[tc]

    def merge(self, other):
        """Merge testcases of two documents. Increments all numbers
        of the `other` document accordingly.
        """
        if self.skip and other.skip:
            return TapDocument(version=self.version)
        elif self.skip:
            return other.copy()
        elif other.skip:
            return self.copy()

        greatest = self.get_actual_range()[1]
        if self.range and self.range[1] > greatest:
            greatest = self.range[1]
        offset = greatest + 1

        if self.version != other.version:
            raise ValueError("Versions of merging instances do not correspond")

        new_doc = TapDocument()
        new_doc.version = self.version
        # self.range gets lost
        new_doc.bailout = self.bailout
        new_doc.bailout_index = self.bailout_index

        for tc in self.testcases:
            new_doc.add_testcase(tc.copy())
        for tc in other.testcases:
            cpy = tc.copy()
            if cpy.number is not None:
                cpy.number += offset - 1  # -1 because number starts with 1
            new_doc.add_testcase(cpy)
        # other.range gets lost
        if other.bailout and not new_doc.bailout:
            new_doc.bailout = other.bailout
            new_doc.bailout_index = offset + other.bailout_index
        return new_doc

    def get_failed_testcases(self):
        """Get a set of number of testcases that failed.
        Failed means that are either missing, 'not ok' or after a bailout.
        The plan will only be checked, if all testcases have a number.
        An empty set as return value means all testcases passed and
        `valid` returns True.
        """
        failed = set()
        if self.skip:
            return failed

        all_have_number = True
        for num, tc in enumerate(self.testcases):
            if self.bailout and num >= self.bailout_index:
                break
            if tc.number is None:
                all_have_number = False
            if not tc.field:
                failed.add(tc.number)

        if not all_have_number:
            return failed

        limits = self.range or self.get_actual_range()
        assert limits[0] >= 0 and limits[1] >= 0

        elements = range(limits[0], limits[1])
        for num, tc in enumerate(self.testcases):
            if self.bailout and num >= self.bailout_index:
                break
            try:
                elements.remove(tc.number)
            except KeyError:
                failed.add(tc.number)
        failed.union(map(lambda tc: tc.number, self.testcases))

        return failed

    def valid(self):
        """Did all tests pass successfully?"""
        self.auto_enumerate()

        if self.skip:
            return True
        if self.bailout:
            return False
        if not all([tc.field for tc in self.testcases]):
            return False
        if not self._range_matches():
            return False
        return True

    def bailed(self):
        """Was some bailout triggered during the testruns?"""
        return bool(self.bailout)

    def get_harness_output(self):
        """Return the result string returned by Harness usually"""
        failed = self.get_failed_testcases()
        if failed:
            if self.range:
                range_len = len(range(*self.range))
            else:
                range_len = len(range(*self.get_actual_range()))

            data = {
                'tests': ', '.join([unicode(f) for f in failed]),
                'failed': len(failed),
                'count': range_len,
                'perc': 1.0 * len(failed) / range_len
            }
            tmpl = (u'FAILED tests {:tests}'
                    u'Failed {:failed}/{:count} tests, {perc:0.2f} okay')
            return tmpl.format(**data)
        else:
            return u'All tests successful.'

    def __enter__(self):
        """Return context for this document"""
        return TapContext(self)

    def __exit__(self, exc_type, exc_value, tracebk):
        """Finalize context for this document"""
        pass

    def __iter__(self):
        """Iterator over testcases. Raises TapBailout Exception if available"""
        if self.skip:
            return iter([])

        iterator = TapDocumentIterator(self.testcases)
        if self.bailout is not None:
            iterator.add_bailout(self.bailout, self.bailout_index)
        return iterator

    def __getitem__(self, tc_number):
        """Return a testcase by its number"""
        for tc in self.testcases:
            if tc.number == int(tc_number):
                return tc
        raise IndexError("No testcase with number {} found".format(tc_number))

    def __unicode__(self, plan_at_beginning=True, plan_comment=u''):
        if self.version >= 13:
            out = u'TAP version {:d}{}'.format(self.version, os.linesep)
        else:
            out = u''
        plan = self.get_actual_plan(plan_comment)
        if self.skip:
            plan += u' # ' + self.skip.strip()

        if plan_at_beginning:
            out += plan + os.linesep
        for tc in self.testcases:
            out += unicode(tc) + os.linesep
        if not plan_at_beginning:
            out += plan + os.linesep

        return out

    def __str__(self):
        return unicode(self).encode(sys.getdefaultencoding())

    def copy(self):
        """Return a copy of myself"""
        doc = TapDocument()
        doc.__setstate__(self.__getstate__())
        return doc

    def __getstate__(self):
        """Return object state for external storage"""
        data = {
            'version': self.version,
            'testcases': [tc.__getstate__() for tc in self.testcases],
            'skip': self.skip
        }
        if self.range:
            data['range'] = self.range
        if self.bailout:
            data['bailout'] = (self.bailout_index, self.bailout)
        return data

    def __setstate__(self, obj):
        """Import data using the provided object"""
        self.version = int(obj['version'])
        self.testcases = []
        self.skip = obj['skip']
        for new_tc in obj['testcases']:
            tc = TapTestcase()
            tc.__setstate__(new_tc)
            self.testcases.append(tc)

        if obj.get('range'):
            self.range = obj['range']
        if obj.get('bailout'):
            self.bailout = obj['bailout'][1]
            self.bailout_index = obj['bailout'][0]


class TapDocumentReader(object):
    """Lexer and parser for TAP documents.
    Use `from_string` or `from_file` method to parse input.
    Use the `document` member to retrieve an instance of `TapDocument`.



    In general this document is an immutable object.
    You can call `from_file` or `from_string` to parse a TAP document.
    After that, the document cannot be modified. Unofficially you can
    also call `add_line` to add line-by-line after the document has been
    read and it will still modify the document. However, there is no
    interface to modify the document 
    
    """

    VERSION_REGEX = re.compile(
        r'^TAP version (?P<version>\d+){nl}'.format(nl=os.linesep),
        flags=re.IGNORECASE
    )
    VERSION_LOOKALIKE = 'TAP VERSION'
    PLAN_REGEX = re.compile(
        r'^(?P<range>(\d+)\.\.(\d+))'
        r'(?P<comment>\s*#.*?)?{nl}'.format(nl=os.linesep),
        flags=re.IGNORECASE
    )
    PLAN_LOOKALIKE = '1..'
    TESTCASE_REGEX = re.compile((r'^'
         r'\s*(?P<field>(not )?ok)'
         r'([ \t]+(?P<number>\d+))?'
         r'([ \t]+(?P<description>[^\n]*?))?'
         r'([ \t]+#(?P<directive>([ \t]+(TODO|SKIP)[^\n]*?)+?))?'
         r'{nl}').format(nl=os.linesep), flags=re.IGNORECASE
    )
    TESTCASE_DATA_REGEX = re.compile(
        r'^(?P<data>[^\n]*{nl})'.format(nl=os.linesep)
    )
    BAILOUT_REGEX = re.compile(
        r'^Bail out!(?P<comment>.*)',
        flags=re.MULTILINE | re.IGNORECASE
    )

    def __init__(self, logger=None):
        """Constructor.

        :param logging.Logger logger:  A logger to use during parsing
        """
        self.document = TapDocument()
        self.log = logger or logging.getLogger(self.__class__.__name__)

    @staticmethod
    def parse_data(data):
        parts = re.split(u'(\n|^)\s*(\.\.\.|---)', data)
        if len(parts) <= 1:
            return data

        try:
            # remove leading and trailing empty lines
            while re.match('^\s*$', parts[0]):
                parts = parts[1:]
            while re.match('^\s*$', parts[-1]):
                parts = parts[:-1]
        except IndexError:
            return u''  # empty text

        output = []
        yaml_mode = False
        for part in parts:
            if re.match(u'^(\n|^)\s*\.\.\.', part):
                yaml_mode = False
                continue
            elif re.match(u'(\n|^)\s*---', part):
                yaml_mode = True
                continue

            if yaml_mode:
                if part:
                    part = yamlish.load(part)
                else:
                    part = None
            if part is not None:
                output.append(part)

        return output

    @staticmethod
    def skip_comment(string):
        """If the first lines are comments (#), skip them"""
        index = 0
        while string[index:].lstrip().startswith('#'):
            match = re.match('#(.*?)' + os.linesep, string[index:])
            index += len(match.group(0))
        return index

    @staticmethod
    def get_range_elements(start, end):
        """Return all elements part of the range.
        For example the range '1..3' contains elements {1, 2, 3}.
        """
        start, end = int(start), int(end)
        if end < start:
            return []
        else:
            return set(range(start, end + 1))

    def parse_possible_version(self, string):
        """If string starts with version info, read it"""
        match = self.VERSION_REGEX.match(string)
        if match:
            self.version = int(match.groupdict()['version'])
            return len(match.group(0))
        else:
            if string.startswith(self.VERSION_LOOKALIKE):
                self.log.info("String '{} ...' looks like a version, "
                    "but does not match.".format(string[0:20]))
            return 0

    def parse_possible_plan(self, string):
        """If string starts with a plan, read it"""
        match = self.PLAN_REGEX.match(string)
        if match:
            limits = [int(v) for v in match.groupdict()['range'].split('..')]
            comment = match.groupdict()['comment']
            if comment and 'skip' in comment.lower():
                self.document.skip = comment.strip()
            self.document.add_range(*limits)
            return len(match.group(0))
        else:
            if string.startswith(self.PLAN_LOOKALIKE):
                self.log.info("String '{} ...' looks like a plan, "
                    "but does not match.".format(string[0:20]))
            return 0

    def parse_possible_testcase(self, string):
        """If string starts with a testcase, read it"""
        orig_len = len(string)
        if not string.endswith(os.linesep):
            string += os.linesep
        match = self.TESTCASE_REGEX.match(string)
        if match:
            tc, groups = TapTestcase(), match.groupdict()

            field = groups['field']
            # must be uppercase
            if field in ['not ok', 'ok']:
                tc.field = field
            else:
                return 0

            tc.number = groups['number']
            tc.directive = groups['directive']

            if groups['description']:
                if groups['description'].startswith('- '):
                    tc.description = groups['description'][2:]
                else:
                    tc.description = groups['description']

            string = string[len(match.group(0)):]
            offset = len(match.group(0))

            data = u''
            while True:
                match1 = self.TESTCASE_REGEX.match(string)
                match2 = self.BAILOUT_REGEX.match(string)
                match3 = self.PLAN_REGEX.match(string)

                if not (match1 or match2 or match3):
                    match = self.TESTCASE_DATA_REGEX.match(string)
                    if not match:
                        break
                else:
                    break

                data += match.groupdict()['data']
                string = string[len(match.group(0)):]

            tc.data = self.parse_data(data)
            self.document.add_testcase(tc)
            return min(orig_len, offset + len(data))
        else:
            return 0

    def parse_possible_bailout(self, string):
        """If string starts with a bailout, read it"""
        match = self.BAILOUT_REGEX.match(string)
        if match:
            comment = match.groupdict()['comment']
            self.document.add_bailout(comment.strip())
            return len(match.group(0))
        else:
            return 0

    def check_bad_strings(self, string):
        if string.startswith(self.VERSION_LOOKALIKE):
            self.log.info("String '{} ...' looks like a version, "
                "but its not allowed here".format(string[:20]))
        if string.startswith(self.PLAN_LOOKALIKE):
            self.log.info("String '{} ...' looks like a plan, "
                "but its not allowed here".format(string[:20]))

    def from_string(self, string, lenient=True):
        """Parse the given string. Raises ``TapParseError``
        for invalid syntax.

        If lenient == True
          lines like "1..3a" will not be considered as invalid plan,
          but normal comments.
        """
        plan_read = False
        string = string.lstrip('\r\n')
        if not string.endswith(os.linesep):
            string += os.linesep
        index = 0

        # version and plan
        index += self.parse_possible_version(string[index:])
        index += self.skip_comment(string[index:])
        prev = index
        index += self.parse_possible_plan(string[index:])
        if prev != index:
            plan_read = True
        index += self.skip_comment(string[index:])

        while True:
            # testcase or bailout
            self.check_bad_strings(string[index:])
            change = self.parse_possible_testcase(string[index:])
            index, tc_parsed = index + change, bool(change)

            change = self.parse_possible_plan(string[index:])
            if change and plan_read:
                raise TapParseError("Plan read twice")
            if change:
                index += change
                plan_read = True
                break

            if tc_parsed:
                self.check_bad_strings(string[index:])
            change = self.parse_possible_bailout(string[index:])
            index, bailout_parsed = index + change, bool(change)

            if bailout_parsed:
                self.check_bad_strings(string[index:])

            if not (tc_parsed or bailout_parsed):
                break

        if not plan_read:
            raise TapParseError("Missing a master plan like '1..3'")

        if string[index:].strip():  # if some text remains, error
            msg = "Some text could not be parsed: '{} ...'"
            raise TapParseError(msg.format(string[index:index + 20]))

        self.auto_enumerate()

    def from_file(self, filepath, encoding='utf-8'):
        """Parse a TAP document provided at `filepath`.
        Raises ``TapParseError`` for invalid syntax.
        """
        with codecs.open(filepath, encoding=encoding) as fp:
            self.from_string(fp.read())


class TapStream(io.TextIOBase):
    """A stream object to read. Conforms to `Text I/O`_ (even though it
    is meant to work with py3k).

    .. _`Text I/O`: http://legacy.python.org/dev/peps/pep-3116/#text-i-o
    """

    def __init__(self, buffer, encoding=None, errors=None,
        newline=None, line_buffering=False):
        super(TapStream, self).__init__(self, buffer, encoding, errors,
            newline, line_buffering)
        self.doc = TapDocument()
        # {'version', 'plan', 'bailout', 'testcase'} (or any subset)
        self.write_mode = set(['plan', 'testcase', 'version', 'bailout'])
        self.bailout_was_last = False

    def __enter__(self):
        """Return context for this stream"""
        return TapContext(self)

    def __exit__(self, exc_type, exc_value, tracebk):
        """Finalize context for this document"""
        pass

    def read(self, n=-1):
        """Read and return at most `n` characters from the stream
        as a single `unicode`. If `n` is negative or None, reads until EOF."""
        representation = unicode(self.doc)
        if n == -1 or n is None:
            self.seek(0, io.SEEK_END)
            return representation[self.tell():]
        else:
            sliced = representation[self.tell():self.tell() + n]
            self.seek(self.tell() + n, io.SEEK_SET)
            return sliced

    def write(self, b=''):
        """Returns number of bytes written, which may be ``< len(b)``."""
        def read_plan(string):
            match = TapDocumentReader.PLAN_REGEX.match(string)
            if match:
                range_spec = [int(v) for v in match.group('range').split('..')]
                string = string[len(match.group(0)):]
                self.doc.add_range(*range_spec)
                # comment gets lost
                self.bailout_was_last = False
                # Plan has been read. No one more.
                self.write_mode.remove('plan')

        enc = self.encoding or locale.getpreferredencoding()
        string = self.buffer + b.decode(enc, errors='strict')
        index = 0
        remaining_bytes = 0

        if 'version' in self.write_mode:
            string = string.lstrip()
            match = TapDocumentReader.VERSION_REGEX.match(string)
            if match:
                self.bailout_was_last = False
                self.doc.set_version(match.group('version'))
                string = string[len(match.group(0)):]
            self.write_mode.remove('version')

        if 'plan' in self.write_mode:
            string = read_plan(string)

        done = not bool(string)
        while not done:
            s = len(string)

            if string.startswith(TapDocumentReader.VERSION_LOOKALIKE):
               raise ValueError('Cannot read version in the middle of string')
            if (string.startswith(TapDocumentReader.PLAN_LOOKALIKE) and
                'plan' not in self.write_mode):
                raise ValueError('Plan has already been read')

            if 'plan' in self.write_mode:
                string = read_plan(string)

            if 'bailout' in self.write_mode:
                match = TapDocumentReader.BAILOUT_REGEX.match(string)
                if match:
                    string = string[len(match.group(0)):]
                    self.doc.add_bailout(match.group('comment').strip())
                    self.bailout_was_last = True

            if 'testcase' in self.write_mode:
                match = TapDocumentReader.TESTCASE_REGEX.match(string)
                if match:
                    string = string[len(match.group(0)):]
                    self.bailout_was_last = False
                    tc = TapTestcase()
                    tc.field = (match.group('field') == 'ok') and True or False
                    tc.number = int(match.group('number'))
                    tc.description = match.group('description').strip()
                    tc.directive = match.group('directive').strip()

                    self.doc.add_testcase(tc)

            if string and len(doc.testcases) > 0:
                data = self.doc.testcases[-1].data
                line = string[0:string.index(self.newline or '\n')]
                string = string[len(line):]
                doc.testcases[-1].data += line

            if len(string) == s:
                self.buffer += string
                remaining_bytes = len(string.encode(enc))
                done = True

        self.auto_enumerate()
        return len(b) - remaining_bytes

    def truncate(self, pos=None):
        raise NotImplementedError("Truncating is unsupported by TapStream")
        #return int

    def readline(self, limit=-1):
        """Read and return one line from the stream. If `limit` is specified,
        at most `limit` bytes will be read.

        The newlines argument to open() can be used to select
        the line terminator(s) recognized.
        """
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
        representation = unicode(self.doc)
        try:
            index = representation[self.tell()]
            return self.readline()
        except IndexError:
            raise StopIteration('End of stream reached')

    def flush(self):
        """Flush the cache and parse its content."""
        self.write()
        if len(self.buffer) > 0:
            buf = self.buffer[0:20]
            if len(buf) == 20:
                buf += ' ...'
            msg = "Some text could not be parsed: '{}'"
            raise TapParseError(msg.format(buf))

    def __iter__(self):
        """Returns an iterator that returns lines from the file
        (which happens to be ``self``).
        """
        return iter(unicode(self.doc))


class TapContext(object):
    """A context manager to write tap files.
    Provides a clean procedural API per document.
    All methods besides `write` and `get` return self;
    thus allowing method chaining.
    """

    def __init__(self, doc=None):
        """Take a `doc` (or create a new one) and provide a context for it"""
        self.doc = doc or TapDocument()
        self.plan_was_written = False
        self.last_element = None

    def plan(self, start=None, end=None, tests=None):
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

        self.doc.add_range(start, end)
        self.plan_was_written = True
        self.last_element = 'plan'

        return self

    def comment(self, comment):
        """Add a comment at the current position."""
        if not self.doc.testcases:
            raise RuntimeError("Sorry, cannot add comment without testcases")

        data = self.doc.testcases[-1].data
        if isinstance(data, basestring):
            self.doc.testcases[-1].data += comment
        else:
            self.doc.testcases[-1].append(comment)

    def _add_tc(self, field, comment, data=None, skip=False, todo=False):
        tc = TapTestcase()
        tc.field = field
        tc.description = comment
        tc.skip = skip
        tc.todo = todo
        if data:
            tc.data = data

        self.doc.add_testcase(tc)
        self.doc.auto_enumerate()

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
        return self.doc

    def bailout(comment=u''):
        """Trigger a bailout"""
        self.doc.add_bailout(comment)
        self.last_element = 'bailout'
        return self

    def write(stream=sys.stderr):
        """Write the document to stderr"""
        print(unicode(doc), file=stream)
