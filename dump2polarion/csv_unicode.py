# -*- coding: utf-8 -*-
"""CSV Unicode Reader."""

import csv


def get_csv_reader(csvfile, dialect=csv.excel, **kwds):
    """Returns csv reader."""
    return csv.reader(csvfile, dialect=dialect, **kwds)
