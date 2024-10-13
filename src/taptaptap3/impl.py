#!/usr/bin/env python3

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


from .exc import TapParseError, TapBailout, TapMissingPlan, TapInvalidNumbering

import re
import os
import sys
import copy
import yaml
import codecs
import logging
import typing
import collections

__all__ = [
    "YamlData",
    "TapTestcase",
    "TapNumbering",
    "TapActualNumbering",
    "TapDocument",
    "TapDocumentValidator",
    "TapDocumentIterator",
    "TapDocumentActualIterator",
    "TapDocumentFailedIterator",
    "TapDocumentTokenizer",
    "TapDocumentParser",
    "TapProtocol",
    "TapWrapper",
    "merge",
]


class YamlData:
    """YAML data storage"""

    def __init__(self, data: dict):
        self.data = data

    def __eq__(self, other) -> bool:
        if hasattr(other, 'data'):
            return self.data == other.data
        else:
            return self.data == other

    def __iter__(self):
        return iter(self.data)

    def __str__(self) -> str:
        return yaml.safe_dump(self.data, explicit_start=True, explicit_end=True)


class TapTestcase:
    """Object representation of an entry in a TAP file"""
    is_testcase: bool = True
    is_bailout: bool = False

    def __init__(self, field: typing.Optional[bool]=None, number: typing.Optional[int]=None, description: str=""):
        # test line
        self._field: typing.Optional[bool] = field
        self._number: typing.Optional[int] = number
        self.description: str = description
        self._directives: typing.MutableMapping[str, typing.List[str]] = {"skip": [], "todo": []}
        # data
        self._data: typing.List[str] = []

    @staticmethod
    def indent(text: str, indent: int=2) -> str:
        """Indent all lines of ``text`` by ``indent`` spaces"""
        return re.sub("(^|\n)(?!\n|$)", "\\1" + (" " * indent), text)

    @property
    def field(self) -> typing.Optional[bool]:
        """A TAP field specifying whether testcase succeeded"""
        return self._field

    @field.setter
    def field(self, value: typing.Optional[typing.Union[bool, str]]) -> None:
        errmsg = "field value must be 'ok' or 'not ok', not {!r}".format(value)
        try:
            if value in [None, True, False]:
                self._field = value
            elif value.rstrip() == "ok":
                self._field = True
            elif value.rstrip() == "not ok":
                self._field = False
            else:
                raise ValueError(errmsg)
        except AttributeError:
            raise ValueError(errmsg)

    @field.deleter
    def field(self):
        self._field = None

    @property
    def number(self) -> typing.Optional[int]:
        """A TAP testcase number"""
        return self._number

    @number.setter
    def number(self, value: typing.Optional[int]) -> None:
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
    def number(self) -> None:
        self._number = None

    @property
    def directive(self) -> str:
        """A TAP directive like 'TODO work in progress'"""
        out = ""
        for skip_msg in self._directives["skip"]:
            out += "SKIP {} ".format(skip_msg.strip())
        for todo_msg in self._directives["todo"]:
            out += "TODO {} ".format(todo_msg.strip())
        return out and out[:-1] or ""

    @directive.setter
    def directive(self, value: str) -> None:
        # reset
        self._directives["skip"] = []
        self._directives["todo"] = []

        if not value:
            return

        delimiters = ["skip", "todo"]
        value = value.lstrip("#\t ")
        fields = re.split("(" + "|".join(delimiters) + ")", value, flags=re.I)
        parts: typing.List[str] = list(filter(bool, fields))

        if not parts or parts[0].lower() not in delimiters:
            raise ValueError("Directive must start with SKIP or TODO")

        key = None
        key_just_set = False
        for val in parts:
            if val.lower() in delimiters:
                key = val.lower()
                if key_just_set:
                    self._directives[key] = []
                key_just_set = True
            else:
                if key is None:
                    msg = "Directive must be sequence of TODOs and SKIPs"
                    raise ValueError(msg + " but is {}".format(value))
                self._directives[key].append(val)
                key_just_set = False

    @directive.deleter
    def directive(self) -> None:
        self._directives = {}

    @property
    def data(self) -> typing.List[str]:
        """Annotated data (eg. a backtrace) to the testcase"""
        return self._data

    @data.setter
    def data(self, value: typing.List[str]) -> None:
        assert hasattr(value, "__iter__"), "If you set data explicitly, it has to be a list"

        self._data = copy.deepcopy(value)

    @data.deleter
    def data(self) -> None:
        self._data = []

    @property
    def todo(self) -> bool:
        """Is a TODO flag annotated to this testcase?"""
        return bool(self._directives["todo"])

    @todo.setter
    def todo(self, what: str) -> None:
        """Add a TODO flag to this testcase.

        :param str what:    Which work is still left?
        """
        if what:
            self._directives["todo"].append(what)

    @property
    def skip(self) -> bool:
        """Is a SKIP flag annotated to this testcase?"""
        return bool(self._directives["skip"])

    @skip.setter
    def skip(self, why: str) -> None:
        """Add a SKIP flag to this testcase.

        :param str why:    Why shall this testcase be skipped?
        """
        if why:
            self._directives["skip"].append(why)

    def copy(self) -> 'TapTestcase':
        """Return a copy of myself"""
        tc = TapTestcase()
        tc.__setstate__(self.__getstate__())
        return tc

    def __eq__(self, other: object) -> bool:
        """Test equality"""
        members = {'field', 'number', 'description', 'directive', 'data'}

        # verify member existence
        for member in members:
            if not hasattr(other, member):
                return False

        # verify equality
        for member in members:
            # 'number': if one number is None and the other is not, it's fine
            if member == 'number':
                result = ((self.number is None and other.number is not None) or
                          (self.number is not None and other.number is None) or
                          self.number == other.number)
                if not result:
                    return False
            else:
                if getattr(self, member) != getattr(other, member):
                    return False

        return True

    def __getstate__(self) -> typing.Dict[str, typing.Any]:
        """Return object state for external storage"""
        return {
            "field": self.field,
            "number": self.number,
            "description": self.description or "",
            "directives": self._directives,
            "data": self.data,
        }

    def __setstate__(self, obj: typing.Dict[str, typing.Any]) -> None:
        """Import data using the provided object"""
        self.field = obj["field"]
        self.number = obj["number"]
        self.description = obj["description"]
        self._directives = obj["directives"]
        self.data = obj["data"]

    def __repr__(self) -> str:
        """Representation of this object"""
        field = "ok" if self.field else "not ok"
        num = "" if self.number is None else " #{}".format(self._number)
        todo_skip = ""

        if self.todo and self.skip:
            todo_skip = " with TODO and SKIP flag"
        elif self.todo:
            todo_skip = " with TODO flag"
        elif self.skip:
            todo_skip = " with SKIP flag"

        return "<TapTestcase {}{}{}>".format(field, num, todo_skip)

    def __str__(self) -> str:
        """TAP testcase representation as a string object"""
        num, desc, directive = self.number, self.description, self.directive

        out = "ok " if self.field else "not ok "
        if num is not None:
            out += str(num) + " "
        if desc:
            out += "- {} ".format(desc)
        if directive:
            out += " # {} ".format(directive)
        out = out.rstrip()
        if self.data:
            data = [str(d) for d in self.data]
            out += os.linesep + (os.linesep).join(data)

        if out.endswith(os.linesep):
            return out
        else:
            return out + os.linesep


class TapNumbering:
    """TAP testcase numbering. In TAP documents it is called 'the plan'."""

    def __init__(self, first: typing.Optional[int]=None, last: typing.Optional[int]=None, tests: typing.Optional[int]=None, lenient: bool=True):
        """Constructor. Provide `first` and `last` XOR a number of `tests`.

        `first` and `last` are testcase numbers. Both inclusive.

        If `lenient` is False, a decreasing range (except '1..0')
        will raise a TapInvalidNumbering Exception.
        Otherwise it will just be normalized (set `last` to `first`).
        """
        arg_errmsg = "Either provide a first and last or a number of tests"
        if first and last and tests:
            raise ValueError(arg_errmsg)

        if first is not None and last is not None:
            self.first: int = int(first)
            self.length: int = int(last) - int(first) + 1

            if int(last) == 0 and int(first) == 1:
                self.length = 0
            elif int(last) < int(first):
                self.length = 0
                if not lenient:
                    msg = "range {}..{} is decreasing".format(first, last)
                    msg = "Invalid testcase numbering: " + msg
                    raise TapInvalidNumbering(msg)

        elif tests is not None:
            self.first = 1
            self.length = int(tests)

        else:
            raise ValueError(arg_errmsg)

        assert self.first >= 0 and self.length >= 0

    def __len__(self) -> int:
        return self.length

    def __bool__(self) -> bool:
        return True

    def __contains__(self, tc_number: int) -> bool:
        """Is `tc_number` within this TapNumbering range?"""
        return self.first <= tc_number and tc_number < self.first + self.length

    def enumeration(self) -> typing.List[int]:
        """Get enumeration for the actual tap plan."""
        return list(range(self.first, self.first + self.length))

    def inc(self) -> None:
        """Increase numbering for one new testcase"""
        self.length += 1

    def normalized_plan(self) -> str:
        """Return a normalized plan where first=1"""
        return "{:d}..{:d}".format(1, self.length)

    def range(self) -> typing.Tuple[int, int]:
        """Get range of this numbering: (min, max)"""
        return (self.first, self.first + self.length - 1)

    def __getstate__(self) -> typing.Dict[str, typing.Any]:
        return {"first": self.first, "length": self.length}

    def __setstate__(self, state: typing.Dict[str, typing.Any]) -> None:
        self.first = state["first"]
        self.length = state["length"]

    def __iter__(self):
        return iter(range(self.first, self.first + self.length))

    def __str__(self) -> str:
        """Return string representation of plan.
        If it was initially a decreasing range, first=last now.
        """
        return "{:d}..{:d}".format(self.first, self.first + self.length - 1)

    def __repr__(self) -> str:
        return "<TapNumbering {}>".format((self.first, self.length))


class TapActualNumbering(list):
    """TAP testcase numbering. Wrapper for a sequence of testcase numbers."""
    pass


class TapDocument:
    """An object representing a TAP document. Also acts as context manager."""
    DEFAULT_VERSION: int = 13

    def __init__(self, version: int=DEFAULT_VERSION, skip: bool=False):
        # testcases and bailouts
        self.entries: typing.List[typing.Union[TapTestcase, TapBailout]] = []
        self.metadata: typing.Dict[str, typing.Any] = {
            # version line
            "version": version,
            "version_written": False,
            # comment lines before first testcase
            "header_comment": [],
            # TAP plan
            "numbering": None,
            "plan_at_beginning": True,
            "skip": bool(skip),
            "skip_comment": "",
        }

    def __bool__(self) -> bool:
        return True

    @property
    def version(self) -> int:
        """Get TAP version for this document"""
        return self.metadata["version"]

    @property
    def skip(self) -> bool:
        """Was this document skipped in the test run?"""
        return self.metadata["skip"]

    # set information

    def set_version(self, version: int=DEFAULT_VERSION) -> None:
        """Set TAP version of this document"""
        self.metadata["version"] = int(version)

    def set_skip(self, skip_comment: str="") -> None:
        """Set skip annotation for this document"""
        if skip_comment:
            self.metadata["skip"] = True
            self.metadata["skip_comment"] = skip_comment
        else:
            self.metadata["skip"] = False

    def add_version_line(self, version: int=DEFAULT_VERSION) -> None:
        """Add information of version lines like 'TAP version 13'"""
        self.set_version(version)
        self.metadata["version_written"] = True

    def add_header_line(self, line: str) -> None:
        """Add header comment line for TAP document"""
        if line.count(os.linesep) > 1:
            raise ValueError("Header line must only be 1 (!) line")
        line = str(line).rstrip() + os.linesep
        self.metadata["header_comment"] += [line]

    def add_plan(self, first: int, last: int, skip_comment: str="", at_beginning: bool=True) -> None:
        """Add information of a plan like '1..3 # SKIP wip'"""
        self.metadata["plan_at_beginning"] = bool(at_beginning)
        self.metadata["numbering"] = TapNumbering(first=first, last=last)
        if skip_comment:
            self.set_skip(skip_comment)

    def add_testcase(self, tc: TapTestcase) -> None:
        """Add a ``TapTestcase`` instance `tc` to this document"""
        self.entries.append(tc.copy())

    def add_bailout(self, bo: TapBailout) -> None:
        """Add a ``TapBailout`` instance `bo` to this document"""
        self.entries.append(bo.copy())

    # processing

    @staticmethod
    def create_plan(first: int, last: int, comment: str="", skip: bool=False) -> str:
        plan = "{:d}..{:d}".format(first, last)

        if os.linesep in comment:
            raise ValueError("Plan comment must not contain newline")

        if skip:
            if not comment.strip():
                comment = "  # SKIP"
            elif "skip" not in comment.lower():
                comment = "  # SKIP " + comment
            else:
                comment = "  # " + comment.strip()
        else:
            comment = ""

        return plan + comment

    # retrieve information

    def __len__(self) -> int:
        """Return number of testcases in this document"""
        if self.metadata["numbering"]:
            return len(self.metadata["numbering"])
        return self.actual_length()

    def actual_length(self) -> int:
        """Return actual number of testcases in this document"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase:
                count += 1
        return count

    def range(self) -> typing.Tuple[int, int]:
        """Get range like ``(1, 2)`` for this document"""
        if not self.metadata["numbering"]:
            return (1, 0)

        return self.metadata["numbering"].range()

    def actual_range(self) -> typing.Tuple[int, int]:
        """Get actual range"""
        if not self.metadata["numbering"] or not self.entries:
            return (1, 0)

        validator = TapDocumentValidator(self)
        enum = validator.enumeration()
        return (min(enum), max(enum))

    def plan(self, comment: str="", skip: bool=False) -> str:
        """Get plan for this document"""
        options = {
            "comment": self.metadata["skip_comment"],
            "skip": self.metadata["skip"],
        }
        return self.create_plan(*self.range(), **options)

    def actual_plan(self) -> str:
        """Get actual plan for this document"""
        options = {
            "comment": self.metadata["skip_comment"],
            "skip": self.metadata["skip"],
        }
        return self.create_plan(*self.actual_range(), **options)

    def count_not_ok(self) -> int:
        """How many testcases which are 'not ok' are there?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and not entry.field:
                count += 1
        return count

    def count_ok(self) -> int:
        """How many testcases which are 'ok' are there?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.field:
                count += 1
        return count

    def count_todo(self) -> int:
        """How many testcases are still 'todo'?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.todo:
                count += 1
        return count

    def count_skip(self) -> int:
        """How many testcases got skipped in this document?"""
        count = 0
        for entry in self.entries:
            if entry.is_testcase and entry.skip:
                count += 1
        return count

    def bailed(self) -> bool:
        """Was a Bailout called at some point in time?"""
        for entry in self.entries:
            if entry.is_bailout:
                return True
        return False

    def bailout_message(self) -> typing.Optional[str]:
        """Return the first bailout message of document or None"""
        for entry in self.entries:
            if entry.is_bailout:
                return entry.msg
        return None

    def valid(self) -> bool:
        """Is this document valid?"""
        validator = TapDocumentValidator(self)
        return validator.valid()

    def __contains__(self, num: int) -> bool:
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

    def __getitem__(self, num: int) -> typing.Optional[typing.Union[TapTestcase, TapBailout]]:
        """Return testcase with the given number.

        - Requires validation and therefore plan beforehand
        - Returns copy of testcase or None (if range specifies existence)
        - Raises IndexError (if testcase does not exist at all)

        :param num:         Testcase number to look up
        """
        try:
            num = int(num)
        except ValueError:
            raise IndexError("Indexing requires testcase number")

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

        return None

    def __iter__(self):
        """Get iterator for testcases"""
        return TapDocumentIterator(self)

    def __getstate__(self) -> typing.Dict[str, typing.Any]:
        """Return state of this object"""
        state = copy.copy(self.metadata)
        state["entries"] = [entry.__getstate__() for entry in self.entries]
        if state["numbering"]:
            state["numbering"] = state["numbering"].__getstate__()
        return state

    def __setstate__(self, state: typing.Dict[str, typing.Any]) -> None:
        """Restore object's state from `state`"""
        self.entries = []
        self.metadata = {}

        for key, value in state.items():
            if key == "entries":
                for entry in value:
                    tc = TapTestcase()
                    tc.__setstate__(entry)
                    self.entries.append(tc)
            elif key == "numbering":
                if value is None:
                    self.metadata[key] = None
                else:
                    self.metadata[key] = TapNumbering(tests=0)
                    self.metadata[key].__setstate__(value)
            else:
                self.metadata[key] = value

        keys_exist = [
            "version",
            "version_written",
            "header_comment",
            "numbering",
            "skip",
            "skip_comment",
        ]
        for key in keys_exist:
            if key not in self.metadata:
                raise ValueError("Missing key {} in state".format(key))

    def copy(self) -> 'TapDocument':
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

    def __str__(self) -> str:
        """String representation of TAP document"""
        out = ""
        # version line
        if (
            self.metadata["version_written"]
            or self.metadata["version"] != self.DEFAULT_VERSION
        ):
            out += "TAP version {:d}".format(self.metadata["version"])
            out += os.linesep
        # header comments
        for comment in self.metadata["header_comment"]:
            out += str(comment)
        # [possibly] plan
        if self.metadata["plan_at_beginning"]:
            out += self.plan() + os.linesep
        # testcases and bailouts
        for entry in self.entries:
            out += str(entry)
        # [possibly] plan
        out += self.plan() if not self.metadata["plan_at_beginning"] else ""

        return out


class TapDocumentValidator:
    """TAP testcase numbering. In TAP documents it is called 'the plan'."""

    def __init__(self, doc: TapDocument, lenient: bool=True):
        """Constructor.

        :param TapDocument doc:   the TAP document to validate
        :param bool lenient:      if True, data inconsistencies, like duplicate use of test case numbers, does not raise an exception
        """
        self.lenient: bool = lenient
        self.skip: bool = doc.skip
        self.bailed: bool = doc.bailed()

        if not doc.metadata["numbering"]:
            raise TapMissingPlan("Plan required before document validation")

        # retrieve numbers and range
        self.numbers: typing.List[typing.Optional[int]] = []
        self.validity: bool = True
        for entry in doc.entries:
            if entry.is_testcase:
                self.numbers.append(entry.number)
                if not entry.field and not entry.skip:
                    self.validity = False
        self.range: typing.Tuple[int, int] = doc.range()

        # prepare enumeration
        self.enum: typing.Optional[typing.List[int]] = None

    def test_range_validity(self) -> None:
        """Is `range` valid for `numbers`? If not, raise an exception"""
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
        # numbers = set()
        # for index, nr in enumerate(self.numbers):
        #    if nr is not None:
        #        if nr in numbers:
        #            msg = "Testcase number {} used twice at indices {} and {}"
        #            first_index = self.numbers.index(nr)
        #            raise ValueError(msg.format(nr, index, first_index))
        #        numbers.add(nr)

    @staticmethod
    def enumerate(numbers: typing.List[typing.Optional[int]], first: int=1, lenient: bool=False):
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
        assigned: typing.Set[int] = set()
        fixed: typing.Set[int] = set()
        sequence: typing.List[int] = []
        next_number: int = 1

        reuse_errmsg = "Testcase number {} was already used"

        def get_next_number(nr: int) -> int:
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
                    sequence = [(next_number if e == nr else e) for e in sequence]
                    sequence.append(nr)

                    next_number += 1
                else:
                    fixed.add(nr)
                    sequence.append(nr)
                    if nr > next_number:
                        next_number = nr + 1

        return sequence

    def all_exist(self) -> bool:
        """Do all testcases in specified `range` exist?"""
        self.enumeration()
        try:
            for i in range(self.range[0], self.range[1] + 1):
                self.enum.index(i)
            return True
        except ValueError:
            return False

    def __bool__(self) -> bool:
        return self.valid()

    def enumeration(self, lenient: bool=True) -> typing.List[int]:
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

    def __repr__(self) -> str:
        return "<TapDocumentValidator {} {}{}>".format(
            self.numbers, self.range, self.enum and " with enumeration" or ""
        )

    def sanity_check(self, lenient: bool=True) -> None:
        """Raise any errors which indicate that this document is wrong.
        This method performs a subset of checks of `valid`, but raises errors
        with meaningful messages unlike `valid` which just returns False.

        :param bool lenient:    Shall I ignore more complex errors?
        """
        self.test_range_validity()
        self.enumerate(self.numbers, self.range[0], lenient)

    def valid(self, lenient: bool=True) -> bool:
        """Is the given document valid, meaning that `numbers` and `range` match?
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


class TapDocumentIterator:
    """Iterator over enumerated testcase entries of TAP document.
    Returns None for non-defined testcases.
    Raises Bailouts per default.
    """

    def __init__(self, doc: TapDocument, raise_bailout: bool=True):
        self.skip: bool = doc.skip
        self.entries: typing.List[typing.Union[TapTestcase, TapBailout]] = copy.deepcopy(doc.entries)
        self.enum: typing.Optional[typing.List[int]] = TapDocumentValidator(doc).enumeration()
        self.current, self.end = doc.range()
        self.raise_bailout: bool = raise_bailout

    def __iter__(self):
        return self

    def lookup(self, num: int) -> typing.Optional[TapTestcase]:
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

        return None

    def __next__(self) -> typing.Optional[TapTestcase]:
        if self.skip:
            raise StopIteration("Document gets skipped")
        if self.current > self.end:
            raise StopIteration("End of entries reached")

        self.current += 1
        return self.lookup(self.current - 1)


class TapDocumentActualIterator:
    """Iterator over actual *un*enumerated testcases. Raises Bailouts."""

    def __init__(self, doc: TapDocument, raise_bailout: bool=True):
        self.skip: bool = doc.skip
        self.entries: typing.List[typing.Union[TapTestcase, TapBailout]] = copy.deepcopy(doc.entries)
        self.current: int = 0
        self.raise_bailout: bool = raise_bailout

    def __iter__(self):
        return self

    def __next__(self) -> typing.Optional[TapTestcase]:
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
        return None
            


class TapDocumentFailedIterator:
    """Iterate over all failed testcases; the ones that are 'not ok'.
    Numbers stay 'None'. Ignores Bailouts.
    """

    def __init__(self, doc: TapDocument):
        self.current: int = 0
        self.doc: TapDocument = doc

    def __iter__(self):
        return self

    def __next__(self) -> TapTestcase:
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


class TapDocumentTokenizer:
    """Lexer for TAP document."""

    # just for documentation
    TOKENS: typing.Set[str] = {
        "VERSION_LINE",
        "DATA",
        "PLAN",
        "TESTCASE",
        "BAILOUT",
        "WARN_VERSION_LINE",
        "WARN_PLAN",
        "WARN_TESTCASE",
    }

    # regexi to match lines
    VERSION_REGEX: re.Pattern = re.compile(r"TAP version (?P<version>\d+)\s*$", flags=re.I)
    PLAN_REGEX: re.Pattern = re.compile(
        r"(?P<first>\d+)\.\.(?P<last>\d+)\s*" r"(?P<comment>#.*?)?$"
    )
    TESTCASE_REGEX: re.Pattern = re.compile(
        (
            r"(?P<field>(not )?ok)"
            r"(\s+(?P<number>\d+))?"
            r"(\s+(?P<description>[^\n]*?)"
            r"(\s+#(?P<directive>(\s+(TODO|SKIP).*?)+?))?)?\s*$"
        ),
        flags=re.IGNORECASE,
    )
    BAILOUT_REGEX: re.Pattern = re.compile(
        r"Bail out!(?P<comment>.*)", flags=re.MULTILINE | re.IGNORECASE
    )

    # lookalike matches
    VERSION_LOOKALIKE: str = "tap version"
    PLAN_LOOKALIKE: str = "1.."
    TESTCASE_LOOKALIKE: typing.List[str] = ["not ok ", "ok "]

    def __init__(self):
        self.pipeline: typing.Deque[typing.Any] = collections.deque()
        self.last_indentation: typing.Optional[int] = 0

    @classmethod
    def strip_comment(cls, cmt: typing.Optional[str]) -> str:
        if cmt is None:
            return ""
        return cmt.lstrip().lstrip("#-").lstrip().rstrip()

    def parse_line(self, line: str) -> None:
        """Parse one line of a TAP file"""
        match1 = self.VERSION_REGEX.match(line)
        match2 = self.PLAN_REGEX.match(line)
        match3 = self.TESTCASE_REGEX.match(line)
        match4 = self.BAILOUT_REGEX.match(line)

        add = lambda *x: self.pipeline.append(x)

        if match1:
            add("VERSION_LINE", int(match1.group("version")))
            self.last_indentation = None
        elif match2:
            add(
                "PLAN",
                (int(match2.group("first")), int(match2.group("last"))),
                self.strip_comment(match2.group("comment")),
            )
            self.last_indentation = None
        elif match3:
            number = match3.group("number")
            number = int(number) if number else None
            add(
                "TESTCASE",
                match3.group("field").lower() == "ok",
                number,
                self.strip_comment(match3.group("description")),
                match3.group("directive"),
            )
            self.last_indentation = 0
        elif match4:
            add("BAILOUT", match4.group("comment").strip())
            self.last_indentation = None
        else:
            sline = line.lower().strip()
            lookalike = 'Line "{}" looks like a {}, but does not match syntax'

            if sline.startswith(self.VERSION_LOOKALIKE):
                add("WARN_VERSION_LINE", lookalike.format(sline, "version line"))
            elif sline.startswith(self.PLAN_LOOKALIKE):
                add("WARN_PLAN", lookalike.format(sline, "plan"))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[0]):
                add("WARN_TESTCASE", lookalike.format(sline, "test line"))
            elif sline.startswith(self.TESTCASE_LOOKALIKE[1]):
                add("WARN_TESTCASE", lookalike.format(sline, "test line"))

            add("DATA", line)

    def from_file(self, filepath: str, encoding: str="utf-8") -> None:
        """Read TAP file using `filepath` as source."""
        with codecs.open(filepath, encoding=encoding) as fp:
            for line in fp.readlines():
                self.parse_line(line.rstrip("\n\r"))

    def from_string(self, string: str) -> None:
        """Read TAP source code from the given `string`."""
        for line in string.splitlines():
            self.parse_line(line.rstrip("\n\r"))

    def __iter__(self):
        return self

    def __next__(self):
        try:
            while True:
                return self.pipeline.popleft()
        except IndexError:
            raise StopIteration("All tokens consumed.")


class TapDocumentParser:
    """Parser for TAP documents"""

    def __init__(self, tokenizer: TapDocumentTokenizer, lenient: bool=True, logger: typing.Optional[logging.Logger]=None):
        self.tokenizer: TapDocumentTokenizer = tokenizer
        self.lenient_parsing: bool = lenient
        self.doc: typing.Optional[TapDocument] = None

        if logger:
            self.log: logging.Logger = logger
        else:
            logging.basicConfig()
            self.log = logging.getLogger(self.__class__.__name__)

    @classmethod
    def parse_data(cls, lines: typing.List[str]) -> typing.List[typing.Any]:
        """Give me some lines and I will parse it as data"""
        data: typing.List[typing.Any] = []
        yaml_mode = False
        yaml_cache = ""

        for line in lines:
            if line.strip() == "---":
                yaml_mode = True
            elif yaml_mode and line.strip() == "...":
                data.append(YamlData(yaml.safe_load(yaml_cache)))
                yaml_cache = ""
                yaml_mode = False
            else:
                if yaml_mode:
                    yaml_cache += line + os.linesep
                else:
                    line = line.rstrip("\r\n")
                    if len(data) > 0 and isinstance(data[-1], str):
                        data[-1] += line + os.linesep
                    else:
                        data.append(line + os.linesep)
        return data

    def warn(self, msg: str) -> None:
        """Raise a warning with text `msg`"""
        if self.lenient_parsing:
            self.log.warning(msg)
        else:
            raise TapParseError(msg)

    def parse(self) -> None:
        """Parse the tokens provided by `self.tokenizer`."""
        self.doc = TapDocument()
        state = 0
        plan_written = False
        comment_cache: typing.List[str] = []

        def flush_cache(comment_cache: typing.List[str]) -> typing.List[str]:
            if comment_cache:
                if self.doc.entries:
                    self.doc.entries[-1].data += self.parse_data(comment_cache)
                else:
                    for line in self.parse_data(comment_cache):
                        self.doc.metadata["header_comment"] += [line]
                comment_cache = []
            return comment_cache

        for tok in self.tokenizer:
            if tok[0] == "VERSION_LINE":
                if state != 0:
                    msg = "Unexpected version line. " "Must only occur as first line."
                    raise TapParseError(msg)
                self.doc.add_version_line(tok[1])
                state = 1
            elif tok[0] == "PLAN":
                comment_cache = flush_cache(comment_cache)
                if plan_written:
                    msg = "Plan must not occur twice in one document."
                    raise TapParseError(msg)
                if tok[1][0] > tok[1][1] and not (tok[1] == (1, 0)):
                    self.warn("Plan defines a decreasing range.")

                self.doc.add_plan(tok[1][0], tok[1][1], tok[2], state <= 1)
                state = 2
                plan_written = True
            elif tok[0] == "TESTCASE":
                comment_cache = flush_cache(comment_cache)

                tc = TapTestcase()
                tc.field = tok[1]
                tc.number = tok[2] if tok[2] else None
                tc.description = tok[3] if tok[3] else None
                tc.directive = tok[4] if tok[4] else None

                self.doc.add_testcase(tc)
                state = 2
            elif tok[0] == "BAILOUT":
                comment_cache = flush_cache(comment_cache)

                self.doc.add_bailout(TapBailout(tok[1]))
                state = 2
            elif tok[0] == "DATA":
                comment_cache.append(tok[1])
                state = 2
            elif tok[0] in ["WARN_VERSION_LINE", "WARN_PLAN", "WARN_TESTCASE"]:
                self.warn(tok[1])
                state = 2
            else:
                raise ValueError("Unknown token: {}".format(tok))

        comment_cache = flush_cache(comment_cache)
        return None

    @property
    def document(self) -> typing.Optional[TapDocument]:
        if not self.doc:
            self.parse()
        return self.doc


class TapProtocol:
    """The interface/protocol of a TAP implementation"""

    def __init__(self, version: int=TapDocument.DEFAULT_VERSION):
        return NotImplemented

    def plan(self, first: int, last: int, skip: str="") -> 'TapProtocol':
        raise NotImplementedError()

    def testcase(self, ok: bool, description: str="", skip: str="", todo: str="") -> 'TapProtocol':
        raise NotImplementedError()

    def bailout(self, comment: str) -> 'TapProtocol':
        raise NotImplementedError()

    def write(self, line: str):
        raise NotImplementedError()

    def finalize(self) -> 'TapProtocol':
        return NotImplemented


class TapWrapper(TapProtocol):
    """One of the nice TAP APIs. See ``api`` module for others.

    Wraps a `TapDocument` and provides the nicer `TapProtocol` API.
    All methods besides `write` and `get` return self;
    thus allowing method chaining. `plan` can be called at any time
    unlike the TAP file format specification defines.
    """

    def __init__(self, doc: typing.Optional[TapDocument]=None, version: int=TapDocument.DEFAULT_VERSION):
        """Take a `doc` (or create a new one)"""
        self.doc: TapDocument = doc or TapDocument(version)
        self._plan: typing.Optional[typing.Tuple[int, int, str]] = None

    def plan(self, first: typing.Optional[int]=None, last: typing.Optional[int]=None, skip: str="", tests: typing.Optional[int]=None) -> 'TapWrapper':
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

    def write(self, line: str) -> 'TapWrapper':
        """Add a comment `line` at the current position."""
        if self.doc.entries:
            self.doc.entries[-1].data += [line]
        else:
            self.doc.add_header_line(line)
        return self

    def testcase(self, ok: bool=True, description: str="", skip: bool=False, todo: bool=False) -> 'TapWrapper':
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

    def ok(self, description: str="", skip: bool=False, todo: bool=False) -> 'TapWrapper':
        """Add a succeeded testcase entry to the TapDocument"""
        self.testcase(True, description, skip, todo)
        return self

    def not_ok(self, description: str="", skip: bool=False, todo: bool=False) -> 'TapWrapper':
        """Add a failed testcase entry to the TapDocument"""
        self.testcase(False, description, skip, todo)
        return self

    def unwrap(self) -> 'TapDocument':
        """Retrieve a copy of the current document"""
        self.finalize()
        return self.doc.copy()

    def bailout(self, comment: str="") -> 'TapWrapper':
        """Trigger a bailout"""
        self.doc.add_bailout(TapBailout(comment))
        return self

    def out(self, stream=sys.stderr) -> None:
        """Write the document to stderr. Requires finalization."""
        self.finalize()
        print(str(self.doc), file=stream)

    def finalize(self) -> 'TapWrapper':
        """Finalize document. Just checks whether plan has been written.
        Any operation afterwards besides `out` and `unwrap` is
        undefined behavior.
        """
        if not self._plan:
            raise TapMissingPlan("Cannot finalize document. Plan required.")
        self.doc.add_plan(
            first=self._plan[0], last=self._plan[1], skip_comment=self._plan[2]
        )
        return self

    def __str__(self) -> str:
        return str(self.doc)


def merge(*docs: TapDocument) -> typing.Optional[TapDocument]:
    """Merge TAP documents provided as argument.
    Takes maximum TAP document version. Testcase numbers are
    incremented by consecutive offsets based on the TAP plan.
    """
    # this is a incredible complex algorithm, just sayin'
    if not docs:
        return None

    doc = TapDocument()
    doc.set_version(max([d.metadata["version"] for d in docs]))

    for d in docs:
        if d.metadata["header_comment"]:
            comments = [c for c in d.metadata["header_comment"] if c.strip()]
            doc.metadata["header_comment"] += comments

    # normalize ranges
    ranges, offset = [], 1
    minimum: float = float("inf")
    maximum: float = 0.
    count: int = 0
    for d in docs:
        r = list(d.range())
        r[1] = max(r[1], r[0] + len(d) - 1)
        r = [x + offset - r[0] for x in r]
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
        for entry in doc.entries[-count_assignments or len(doc.entries) :]:
            if not entry.is_testcase:
                continue
            number = enums[index]
            entry.number = number
            minimum, maximum = min(minimum, number), max(maximum, number)
            index += 1
            count += 1

    skip_comments = []
    for d in docs:
        if d.metadata["skip"] and d.metadata["skip_comment"]:
            skip_comments.append(d.metadata["skip_comment"])

    pab = any([d.metadata["plan_at_beginning"] for d in docs])

    if count == 0:
        minimum, maximum = 1, 0
    elif minimum == float("inf"):
        minimum, maximum = 1, count
    else:
        maximum = max(maximum, minimum + count - 1)

    doc.add_plan(int(minimum), int(maximum), "; ".join(skip_comments), pab)

    return doc
