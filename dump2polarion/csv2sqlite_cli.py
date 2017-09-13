# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV input file to SQLite.
"""

from __future__ import unicode_literals, absolute_import

import argparse
import datetime
import logging
import os
import sqlite3

from dump2polarion import csvtools
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.utils import init_log


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='csv2sqlite')
    parser.add_argument('-i', '--input_file', required=True,
                        help="Path to CSV records file")
    parser.add_argument('-o', '--output_file', required=True,
                        help="Path to sqlite output file")
    parser.add_argument('--log-level',
                        help="Set logging to specified level")
    return parser.parse_args(args)


def dump2sqlite(records, output_file):
    """Dumps tests results to database."""
    results_keys = list(records.results[0].keys())
    keys_len = len(results_keys)
    for key in (
            'verdict', 'last_status', 'exported', 'time', 'comment', 'stdout', 'stderr', 'user1'):
        if key not in results_keys:
            results_keys.append(key)

    conn = sqlite3.connect(os.path.expanduser(output_file), detect_types=sqlite3.PARSE_DECLTYPES)

    # in each row there needs to be data for every column
    pad_data = ['' for _ in range(len(results_keys) - keys_len)]
    # last column is current time
    now = datetime.datetime.utcnow()

    def _extend_row(row):
        if pad_data:
            row.extend(pad_data)
        row.append(now)
        return row

    to_db = [_extend_row(list(row.values())) for row in records.results]

    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE testcases ({},sqltime TIMESTAMP)".format(
            ','.join(['{} TEXT'.format(key) for key in results_keys])))
    cur.executemany("INSERT INTO testcases VALUES ({},?)".format(
        ','.join(['?' for _ in results_keys])), to_db)

    if records.testrun:
        cur.execute("CREATE TABLE testrun (testrun TEXT)")
        cur.execute("INSERT INTO testrun VALUES (?)", (records.testrun, ))

    conn.commit()
    conn.close()

    logger.info("Data written to '{}'".format(output_file))


def main(args=None):
    """Main function for cli."""
    args = get_args(args)

    init_log(args.log_level)

    if '.csv' not in args.input_file.lower():
        logger.warn("Make sure the input file '{}' is in CSV format".format(args.input_file))

    try:
        records = csvtools.get_imported_data(args.input_file)
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        return 1

    # check if all columns required by `pytest_polarion_cfme` are there
    required_columns = {'id': 'ID', 'title': 'Title'}
    missing_columns = [required_columns[k] for k in required_columns if k not in records.results[0]]
    if missing_columns:
        logger.fatal(
            "The input file '{}' is missing following columns: {}".format(
                args.input_file, ', '.join(missing_columns)))
        return 1

    try:
        dump2sqlite(records, args.output_file)
    # pylint: disable=broad-except
    except Exception as err:
        logger.fatal(err)
        return 1

    return 0
