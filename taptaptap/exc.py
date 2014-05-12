#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    exc.py
    ~~~~~~

    Exceptions for TAP file handling.

    (c) BSD 3-clause.
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os
import sys

__all__ = ['TapParseError', 'TapMissingPlan',
           'TapInvalidNumbering', 'TapBailout']


class TapParseError(Exception):
    pass


class TapMissingPlan(TapParseError):
    pass


class TapInvalidNumbering(TapParseError):
    pass


class TapBailout(Exception):
    is_testcase = False
    is_bailout = True
    encoding = sys.stdout.encoding

    def __init__(self, *args, **kwargs):
        super(TapBailout, self).__init__(*args, **kwargs)
        self.data = []

    def __str__(self):
        return unicode(self).encode(self.encoding or 'utf-8')

    def __unicode__(self):
        return u'Bail out! {}{}{}'.format(self.message, os.linesep,
                                          os.linesep.join(self.data))

    def copy(self, memo=None):
        inst = TapBailout(self.message)
        inst.data = self.data
        return inst
