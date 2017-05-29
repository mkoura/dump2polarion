# -*- coding: utf-8 -*-
"""
Allowed values for verdicts.
"""

from __future__ import unicode_literals


class Verdicts(object):
    PASS = ('passed', 'pass')
    FAIL = ('failed', 'fail')
    SKIP = ('skipped', 'skip', 'blocked')
    WAIT = ('null', 'wait', 'waiting')
