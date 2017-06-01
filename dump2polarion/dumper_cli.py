# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV, SQLite, junit or Ostriz input file to xunit file and submit it
to the Polarion® XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import argparse
import logging
import os
import datetime

import dump2polarion
from dump2polarion import Dump2PolarionException, dbtools
from dump2polarion.submit import submit_to_polarion


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='dump2polarion')
    parser.add_argument('-i', '--input_file', required=True,
                        help="Path to CSV or SQLite reports file or xunit XML file")
    parser.add_argument('-o', '--output_file',
                        help="Path to XML output file (default: none)")
    parser.add_argument('-t', '--testrun-id',
                        help="Polarion test run id")
    parser.add_argument('-c', '--config_file',
                        help="Path to config YAML (default: dump2polarion.yaml")
    parser.add_argument('-n', '--no-submit', action='store_true',
                        help="Don't submit results to Polarion")
    parser.add_argument('--user',
                        help="Username to use to submit results to Polarion")
    parser.add_argument('--password',
                        help="Password to use to submit results to Polarion")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Don't validate test run id")
    parser.add_argument('--no-verify', action='store_true',
                        help="Don't verify results submission")
    parser.add_argument('--verify-timeout', type=int, default=300, metavar='SEC',
                        help="How long to wait (in seconds) for verification of results submission"
                             " (default: %(default)s)")
    parser.add_argument('--log-level',
                        help="Set logging to specified level")
    return parser.parse_args(args)


def submit_and_verify(args, config, xunit):
    """Submits results to the XUnit Importer and checks that it was imported."""
    if args.no_verify:
        verification_func = None
    else:
        # avoid slow initialization of stomp when it's not needed
        from dump2polarion import msgbus
        verification_func = msgbus.get_verification_func(
            config, xunit, user=args.user, password=args.password)

    response = submit_to_polarion(xunit, config, user=args.user, password=args.password)

    if verification_func:
        response = verification_func(skip=not response, timeout=args.verify_timeout)

    return bool(response)


def init_log(log_level):
    """Initializes logging."""
    log_level = log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))


def get_testrun_id(args, records):
    """Returns testrun id."""
    if (args.testrun_id and records.testrun and not args.force and
            records.testrun != args.testrun_id):
        raise Dump2PolarionException(
            "The test run id '{}' found in exported data doesn't match '{}'. "
            "If you really want to proceed, add '-f'.".format(records.testrun, args.testrun_id))

    testrun_id = args.testrun_id or records.testrun
    if not testrun_id:
        raise Dump2PolarionException(
            "The testrun id was not specified on command line and not found in the input data.")

    return testrun_id


# pylint: disable=too-many-locals
def main(args=None):
    """Main function for cli."""
    args = get_args(args)

    init_log(args.log_level)

    try:
        config = dump2polarion.get_config(args.config_file)
    except EnvironmentError as err:
        logger.fatal(err)
        return 1

    # select importer based on input file type and load needed tools
    _, ext = os.path.splitext(args.input_file)
    ext = ext.lower()
    if 'ostriz' in args.input_file:
        from dump2polarion import ostriztools
        importer = ostriztools.import_ostriz
    elif ext == '.xml':
        with open(args.input_file) as input_file:
            xunit = input_file.read()

        if 'polarion-testrun-id' in xunit:
            # expect xunit xml and just submit it
            response = submit_and_verify(args, config, xunit)
            return 0 if response else 2

        # expect junit-report from pytest
        from dump2polarion import junittools
        del xunit
        importer = junittools.import_junit
    elif ext == '.csv':
        from dump2polarion import csvtools
        importer = csvtools.import_csv_and_check
    elif ext in ('.sqlite', '.sqlite3', '.db', '.db3'):
        importer = dbtools.import_sqlite
    else:
        logger.fatal(
            "Cannot recognize type of input data, add file extension.")
        return 1

    import_time = datetime.datetime.utcnow()

    try:
        records = importer(args.input_file, older_than=import_time)
        testrun_id = get_testrun_id(args, records)
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        return 1

    exporter = dump2polarion.XunitExport(testrun_id, records, config)
    try:
        output = exporter.export()
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        return 1

    if args.output_file or args.no_submit:
        # when no output file is specified, the 'testrun_TESTRUN_ID-TIMESTAMP'
        # file will be created in current directory
        exporter.write_xml(output, args.output_file)

    if not args.no_submit:
        response = submit_and_verify(args, config, output)

        if importer is dbtools.import_sqlite and response:
            dbtools.mark_exported_sqlite(args.input_file, import_time)

        return 0 if response else 2
