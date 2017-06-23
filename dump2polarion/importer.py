# -*- coding: utf-8 -*-
"""
Import data using correct tools.
"""

from __future__ import unicode_literals, absolute_import

import os

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.dbtools import SQLITE_EXT


def _get_importer(input_file):
    """Selects importer based on input file type."""
    _, ext = os.path.splitext(input_file)
    ext = ext.lower()

    if 'ostriz' in input_file:
        from dump2polarion import ostriztools
        importer = ostriztools.import_ostriz
    elif ext == '.xml':
        # expect junit-report from pytest
        from dump2polarion import junittools
        importer = junittools.import_junit
    elif ext == '.csv':
        from dump2polarion import csvtools
        importer = csvtools.import_csv
    elif ext in SQLITE_EXT:
        from dump2polarion import dbtools
        importer = dbtools.import_sqlite
    else:
        raise Dump2PolarionException(
            "Cannot recognize type of input data, add file extension.")

    return importer


def do_import(input_file, **kwargs):
    """Imports the input file."""

    return _get_importer(input_file)(input_file, **kwargs)
