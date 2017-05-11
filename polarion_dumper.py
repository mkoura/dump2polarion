#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV or SQLite input file to xunit file and submit it
to Polarion® xunit importer.
"""

from __future__ import unicode_literals

import argparse
import logging
import sys
import os

import dump2polarion
from dump2polarion import Dump2PolarionException, csvtools, dbtools


# pylint: disable=invalid-name
logger = logging.getLogger()


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='dump2polarion')
    parser.add_argument('-i', '--input_file', required=True, action='store',
                        help="Path to CSV or SQLite reports file or xunit XML file")
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
    parser.add_argument('--log-level', action='store',
                        help="Set logging to specified level")
    return parser.parse_args()


def main():
    """Main function for cli."""
    args = get_args()

    log_level = args.log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))

    try:
        config = dump2polarion.get_config(args.config_file)
    except EnvironmentError as err:
        logger.fatal(err)
        sys.exit(1)

    _, ext = os.path.splitext(args.input_file)
    ext = ext.lower()
    if ext == '.xml':
        # expect xunit xml and just submit it
        dump2polarion.submit_to_polarion(
            args.input_file, config, user=args.user, password=args.password)
        return
    elif ext == '.csv':
        importer = csvtools.import_csv
    else:
        importer = dbtools.import_sqlite

    try:
        records = importer(args.input_file)
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        sys.exit(1)

    if not args.force and records.testrun and records.testrun != args.testrun_id:
        logger.fatal(
            "The test run id `{}` found in exported data doesn't match `{}`. "
            "If you really want to proceed, add '-f'.".format(records.testrun, args.testrun_id))
        sys.exit(1)

    exporter = dump2polarion.XunitExport(args.testrun_id, records, config)
    output = exporter.export()

    if args.output_file or args.no_submit:
        # when no output file is specified, the 'testrun_TESTRUN_ID-TIMESTAMP'
        # file will be created in current directory
        exporter.write_xml(output, args.output_file)

    if not args.no_submit:
        response = dump2polarion.submit_to_polarion(
            output, config, user=args.user, password=args.password)

        if response is None:
            logger.error("Failed to submit results to {}".format(config.get('xunit_target')))
        elif not response:
            logger.error("HTTP status {} - failed to submit results to {}".format(
                response.status_code, config.get('xunit_target')))
        elif importer is dbtools.import_sqlite:
            # successfully submitted, mark all rows with verdict as exported
            dbtools.mark_exported_sqlite(args.input_file)


if __name__ == '__main__':
    main()
