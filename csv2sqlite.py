#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV input file to SQLite.
"""

from __future__ import print_function, unicode_literals

import argparse
import logging
import sys
import os

import sqlite3
from sqlite3 import Error

import dump2polarion


# pylint: disable=invalid-name
logger = logging.getLogger()


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='csv2sqlite')
    parser.add_argument('-i', '--input_file', required=True, action='store',
                        help="Path to CSV results file")
    parser.add_argument('-o', '--output_file', required=True, action='store',
                        help="Path to sqlite output file")
    return parser.parse_args()


def dump2sqlite(data, output_file):
    """Dumps data to database."""
    data_keys = data[0].keys()
    keys_len = len(data_keys)
    for key in ['verdict', 'last_status', 'time', 'comment', 'stdout', 'stderr', 'exported']:
        if key not in data_keys:
            data_keys.append(key)
    columns = ['{} TEXT'.format(key) for key in data_keys]
    bindings = ','.join(['?' for _ in data_keys])

    # in each row there needs to be data for every column
    pad_data = ['' for _ in range(len(data_keys) - keys_len)]

    def _pad_data(row):
        if pad_data:
            row.extend(pad_data)
        return row

    to_db = [_pad_data(row.values()) for row in data]

    try:
        conn = sqlite3.connect(os.path.expanduser(output_file))
    except Error as err:
        logger.error(err)
        sys.exit(1)

    cur = conn.cursor()
    cur.execute("CREATE TABLE testcases ({})".format(','.join(columns)))
    cur.executemany("INSERT INTO testcases VALUES ({})".format(bindings), to_db)
    conn.commit()
    conn.close()
    logger.info("Data written to '{}'".format(output_file))


def main():
    """Main function for cli."""
    args = get_args()
    tests_results = dump2polarion.import_csv(args.input_file)
    dump2sqlite(tests_results, args.output_file)


if __name__ == '__main__':
    logging.basicConfig(format='%(name)s:%(levelname)s:%(message)s', level=logging.INFO)
    main()
