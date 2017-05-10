#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV input file to SQLite.
"""

from __future__ import unicode_literals

import argparse
import logging
import sys
import os
import sqlite3

from dump2polarion import Dump2PolarionException, csvtools


# pylint: disable=invalid-name
logger = logging.getLogger()


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='csv2sqlite')
    parser.add_argument('-i', '--input_file', required=True, action='store',
                        help="Path to CSV records file")
    parser.add_argument('-o', '--output_file', required=True, action='store',
                        help="Path to sqlite output file")
    return parser.parse_args()


def dump2sqlite(records, output_file):
    """Dumps tests results to database."""
    results_keys = records.results[0].keys()
    keys_len = len(results_keys)
    for key in (
            'verdict', 'last_status', 'exported', 'time', 'comment', 'stdout', 'stderr', 'user1'):
        if key not in results_keys:
            results_keys.append(key)

    conn = sqlite3.connect(os.path.expanduser(output_file))

    # in each row there needs to be data for every column
    pad_data = ['' for _ in range(len(results_keys) - keys_len)]

    def _pad_data(row):
        if pad_data:
            row.extend(pad_data)
        return row

    to_db = [_pad_data(row.values()) for row in records.results]

    cur = conn.cursor()
    cur.execute("CREATE TABLE testcases ({})".format(
        ','.join(['{} TEXT'.format(key) for key in results_keys])))
    cur.executemany("INSERT INTO testcases VALUES ({})".format(
        ','.join(['?' for _ in results_keys])), to_db)

    if records.testrun:
        cur.execute("CREATE TABLE testrun (testrun TEXT)")
        cur.execute("INSERT INTO testrun VALUES (?)", (records.testrun, ))

    conn.commit()
    conn.close()

    logger.info("Data written to '{}'".format(output_file))


def main():
    """Main function for cli."""
    args = get_args()
    try:
        records = csvtools.import_csv(args.input_file)
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        sys.exit(1)

    # check if all columns required by `pytest_polarion_cfme` are there
    results_keys = records.results[0].keys()
    required_columns = {'id': 'ID', 'testcaseid': 'Test Case ID'}
    missing_columns = [required_columns[k] for k in ('id', 'testcaseid') if k not in results_keys]
    if missing_columns:
        logger.fatal(
            "The input file `{}` is missing following columns: {}".format(
                args.input_file, ', '.join(missing_columns)))
        sys.exit(1)

    try:
        dump2sqlite(records, args.output_file)
    # pylint: disable=broad-except
    except Exception as err:
        logger.fatal(err)
        sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(format='%(name)s:%(levelname)s:%(message)s', level=logging.INFO)
    main()
