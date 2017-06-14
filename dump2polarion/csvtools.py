# -*- coding: utf-8 -*-
"""
Helper functions for handling data in CSV format.
"""

from __future__ import unicode_literals, absolute_import

import os
import re
import csv

from collections import OrderedDict

from dump2polarion import ImportedData
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.csv_unicode import UnicodeReader


def get_csv_fieldnames(csv_reader):
    """Finds fieldnames in Polarion exported csv file."""
    fieldnames = []
    for row in csv_reader:
        for col in row:
            field = (col.
                     strip().
                     replace('"', '').
                     replace(' ', '').
                     replace('(', '').
                     replace(')', '').
                     lower())
            fieldnames.append(field)
        if 'id' in fieldnames:
            break
        else:
            # this is not a row with fieldnames
            del fieldnames[:]
    if not fieldnames:
        return
    # remove trailing unannotated fields
    while True:
        field = fieldnames.pop()
        if field:
            fieldnames.append(field)
            break
    # name unannotated fields
    suffix = 1
    for index, field in enumerate(fieldnames):
        if not field:
            fieldnames[index] = 'field{}'.format(suffix)
            suffix += 1

    return fieldnames


def get_testrun_from_csv(file_obj, csv_reader):
    """Tries to find the testrun id in  Polarion exported csv file."""
    file_obj.seek(0)
    search_str = r'TEST_RECORDS:\("[^/]+/([^"]+)"'
    testrun_id = None
    too_far = False
    for row in csv_reader:
        for col in row:
            if not col:
                continue
            field = (col.
                     strip().
                     replace('"', '').
                     replace(' ', '').
                     lower())
            if field == 'id':
                # we are too far, tests results start here
                too_far = True
                break
            search = re.search(search_str, col)
            try:
                testrun_id = search.group(1)
            except AttributeError:
                continue
            else:
                break
        if testrun_id or too_far:
            break

    return testrun_id


def get_results(csv_reader, fieldnames):
    """Maps data to fieldnames.

    The reader needs to be at position after fieldnames, before the results data.
    """
    fieldnames_count = len(fieldnames)
    results = []
    for row in csv_reader:
        for col in row:
            if col:
                break
        else:
            # empty row, skip it
            continue
        record = OrderedDict(zip(fieldnames, row))
        # skip rows that were already exported
        if record.get('exported') == 'yes':
            continue
        row_len = len(row)
        if fieldnames_count > row_len:
            for key in fieldnames[row_len:]:
                record[key] = None
        results.append(record)

    return results


def get_csv_reader(input_file):
    """Returns csv reader."""
    dialect = csv.Sniffer().sniff(input_file.read(2048))
    input_file.seek(0)
    return UnicodeReader(input_file, dialect)


# pylint: disable=unused-argument
def import_csv(csv_file, **kwargs):
    """Reads the content of the Polarion exported csv file and returns imported data."""
    with open(os.path.expanduser(csv_file), 'rb') as input_file:
        reader = get_csv_reader(input_file)

        fieldnames = get_csv_fieldnames(reader)
        if not fieldnames:
            raise Dump2PolarionException(
                "Cannot find field names in CSV file '{}'".format(csv_file))

        results = get_results(reader, fieldnames)
        if not results:
            raise Dump2PolarionException(
                "No results read from CSV file '{}'".format(csv_file))

        testrun = get_testrun_from_csv(input_file, reader)

    return ImportedData(results=results, testrun=testrun)


def import_csv_and_check(csv_file, **kwargs):
    """Like `import_csv` but check that all columns are there."""
    records = import_csv(csv_file, **kwargs)
    required_columns = {'verdict': 'Verdict'}
    missing_columns = [required_columns[k] for k in required_columns if k not in records.results[0]]
    if missing_columns:
        raise Dump2PolarionException(
            "The input file '{}' is missing following columns: {}".format(
                csv_file, ', '.join(missing_columns)))
    return records
