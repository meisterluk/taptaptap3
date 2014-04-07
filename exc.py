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

    def __init__(self, *args, **kwargs):
        super(TapBailout, self).__init__(*args, **kwargs)
        self._data = []

    def __str__(self):
        return u'Bail out! {}'.format(os.linesep.join(self.data))

    @property
    def data(self):
        return [self.message.strip()] + self._data

    @data.setter
    def data(self, value):
        self.message = value[0]
        self._data = value[1:]

    @data.deleter
    def data(self):
        self.message = u''
        self._data = []

    def copy(self):
        return TapBailout(self.message)

    def __getstate__(self):
        return {'bailout': self.message}

    def __setstate__(self, state):
        self.message = state['bailout']
