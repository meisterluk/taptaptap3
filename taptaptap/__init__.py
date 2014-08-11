#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    taptaptap
    ~~~~~~~~~

    An object-oriented module handling the Test Anything Protocol (TAP).
    It's capable of handling TAP files in version 13,
    but will possibly accept older version. See the spec [0]_ [1]_.

    **Remarks:**
    * Implemented for python 2.7
    * I always try to assign a comment to a testcase. As such I assume that
      in a source code like::

          not ok
          Traceback (most recent call last):

      the Traceback line is related to the testcase; not the general document.
      The opposite is not required by the specification.

    Requirements to a TAP document:
    1. There is at least one plan (beginning or end of file)
    2. There is at least one test line in TAP output.
    3. All data structures are immutable. As such I am using some copy operations.

    .. [0] https://metacpan.org/pod/release/PETDANCE/Test-Harness-2.64/lib/Test/Harness/TAP.pod#THE-TAP-FORMAT
    .. [1] http://web.archive.org/web/20120730055134/http://testanything.org/wiki/index.php/TAP_specification

    (c) BSD 3-clause
"""

__author__ = 'Lukas Prokop <admin@lukas-prokop.at>'
__version__ = '1.1'
__license__ = '3-clause BSD license'
__docformat__ = 'reStructuredText'

from .impl import YamlData, TapTestcase, TapNumbering, TapActualNumbering
from .impl import TapDocument, TapDocumentValidator, TapDocumentIterator
from .impl import TapDocumentActualIterator, TapDocumentFailedIterator
from .impl import TapDocumentTokenizer, TapDocumentParser, TapProtocol, TapWrapper
from .impl import merge

from .api import parse_string, parse_file, validate, harness, TapWriter
from .api import TapCreator, SimpleTapCreator, UnittestResult, UnittestRunner

from . import proc
from . import exc
