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

__all__ = ['TapParseError', 'TapMissingPlan', 'TapInvalidNumbering', 'TapBailout']


class TapParseError(Exception):
    pass

class TapMissingPlan(TapParseError):
    pass

class TapInvalidNumbering(TapParseError):
    pass

class TapBailout(Exception):
    is_testcase = False
    is_bailout = True

    def __str__(self):
        message = self.message and (u' ' + self.message) or u''
        return u'Bail out! {}'.format(message.strip())
