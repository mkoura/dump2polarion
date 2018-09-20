# -*- coding: utf-8 -*-
"""CSV Unicode Reader."""

import codecs
import csv


def get_csv_reader(csvfile, dialect=csv.excel, encoding="utf-8", **kwds):
    """Returns csv reader."""
    try:
        # pylint: disable=pointless-statement
        unicode
        return UnicodeReader(csvfile, dialect=dialect, encoding=encoding, **kwds)
    except NameError:
        return csv.reader(csvfile, dialect=dialect, **kwds)


# pylint: disable=too-few-public-methods,non-iterator-returned
class UTF8Recoder(object):
    """Iterator that reads an encoded stream and reencodes the input to UTF-8."""

    def __init__(self, csvfile, encoding):
        self.reader = codecs.getreader(encoding)(csvfile)

    def __iter__(self):
        return self

    def next(self):
        """Returns the next row of the reader’s iterable object."""
        return self.reader.next().encode("utf-8")


# pylint: disable=too-few-public-methods
class UnicodeReader(object):
    """A CSV reader which will iterate over lines in the CSV file.

    The CSV file is encoded in the given encoding.
    """

    def __init__(self, csvfile, dialect=csv.excel, encoding="utf-8", **kwds):
        csvfile = UTF8Recoder(csvfile, encoding)
        self.reader = csv.reader(csvfile, dialect=dialect, **kwds)

    def next(self):
        """Returns the next row of the reader’s iterable object."""
        row = self.reader.next()
        return [s.decode("utf-8") for s in row]

    def __iter__(self):
        return self
