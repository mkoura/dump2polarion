#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV or SQLite input file to xunit file and submit it
to Polarion® xunit importer.
"""

from __future__ import print_function, unicode_literals

import argparse
import logging
import sys
import os
import dump2polarion

from dump2polarion import Dump2PolarionException


# pylint: disable=invalid-name
logger = logging.getLogger()


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='dump2polarion')
    parser.add_argument('-i', '--input_file', required=True, action='store',
                        help="Path to reports CSV or SQLite file")
    parser.add_argument('-o', '--output_file', action='store',
                        help="Path to XML output file (default: none)")
    parser.add_argument('-t', '--testrun-id', required=True, action='store',
                        help="Polarion test run id")
    parser.add_argument('-c', '--config_file', action='store',
                        help="Path to config YAML (default: dump2polarion.yaml")
    parser.add_argument('-n', '--no-submit', action='store_true',
                        help="Don't submit results to Polarion")
    parser.add_argument('--user', action='store',
                        help="Username to use to submit results to Polarion")
    parser.add_argument('--password', action='store',
                        help="Password to use to submit results to Polarion")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Don't validate test run id")
    return parser.parse_args()


def main():
    """Main function for cli."""
    args = get_args()

    try:
        config = dump2polarion.get_config(args.config_file)
    except EnvironmentError as err:
        logger.error(err)
        sys.exit(1)

    _, ext = os.path.splitext(args.input_file)
    if ext.lower() == '.csv':
        importer = dump2polarion.import_csv
    else:
        importer = dump2polarion.import_sqlite

    try:
        records = importer(args.input_file)
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.error(err)
        sys.exit(1)

    if not args.force and records.testrun and records.testrun != args.testrun_id:
        logger.error(
            "The test run id `{}` found in exported data doesn't match `{}` from command line. "
            "If you really want to proceed, add '-f'.".format(records.testrun, args.testrun_id))
        sys.exit(1)

    exporter = dump2polarion.XunitExport(args.testrun_id, records, config)
    output = exporter.export()

    if args.output_file or args.no_submit:
        # when no output file is specified, the 'testrun_TESTRUN_ID-TIMESTAMP'
        # file will be created in current directory
        exporter.write_xml(output, args.output_file)

    if not args.no_submit:
        dump2polarion.submit_to_polarion(output, config, user=args.user, password=args.password)


if __name__ == '__main__':
    logging.basicConfig(format='%(name)s:%(levelname)s:%(message)s', level=logging.INFO)
    main()
