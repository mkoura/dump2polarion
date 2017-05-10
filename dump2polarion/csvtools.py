# -*- coding: utf-8 -*-
"""
Helper functions for handling data in CSV format.
"""

from __future__ import unicode_literals

import os
import re
import csv

from collections import OrderedDict

from . import ImportedData, Dump2PolarionException


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


def get_testrun_from_csv(csv_file, csv_reader):
    """Tries to find the testrun id in  Polarion exported csv file."""
    csv_file.seek(0)
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
                     replace('(', '').
                     replace(')', '').
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


def import_csv(csv_file):
    """Reads the content of the Polarion exported csv file and returns imported data."""
    with open(os.path.expanduser(csv_file), 'rb') as input_file:
        reader = csv.reader(input_file, delimiter=str(';'), quotechar=str('"'))

        fieldnames = get_csv_fieldnames(reader)
        if not fieldnames:
            raise Dump2PolarionException("Cannot find field names in CSV file {}".format(csv_file))
        fieldnames_count = len(fieldnames)

        # map data to fieldnames
        results = []
        for row in reader:
            record = OrderedDict(zip(fieldnames, row))
            # skip rows that were already exported
            if record.get('exported') == 'yes':
                continue
            row_len = len(row)
            if fieldnames_count > row_len:
                for key in fieldnames[row_len:]:
                    record[key] = None
            results.append(record)

        testrun = get_testrun_from_csv(input_file, reader)

    return ImportedData(results=results, testrun=testrun)


def export_csv(csv_file, records):
    """Writes testcases results into csv file."""
    with open(os.path.expanduser(csv_file), 'wb') as output_file:
        csvwriter = csv.writer(output_file, delimiter=str(';'),
                               quotechar=str('|'), quoting=csv.QUOTE_MINIMAL)

        csvwriter.writerow(records.results[0].keys())
        for result in records.results:
            csvwriter.writerow(result.values())
