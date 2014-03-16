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

__all__ = ['TapParseError', 'TapBailout']


class TapParseError(Exception):
    pass


class TapBailout(Exception):
    def __str__(self):
        message = self.message and (u' ' + self.message) or u''
        return u'Bail out!{}'.format(message)
