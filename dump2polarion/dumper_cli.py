# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV, SQLite, junit or Ostriz input file to xunit file and submit it
to the Polarion XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import os
import io
import argparse
import logging
import datetime

import dump2polarion
from dump2polarion import dbtools
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.configuration import get_config
from dump2polarion.submit import submit_and_verify


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='dump2polarion')
    parser.add_argument('-i', '--input_file', required=True,
                        help="Path to CSV or SQLite reports file or xunit XML file")
    parser.add_argument('-o', '--output_file',
                        help="Where to save the XML output file (default: not saved)")
    parser.add_argument('-t', '--testrun-id',
                        help="Polarion test run id")
    parser.add_argument('-c', '--config-file',
                        help="Path to config YAML")
    parser.add_argument('-n', '--no-submit', action='store_true',
                        help="Don't submit results to Polarion")
    parser.add_argument('--user',
                        help="Username to use to submit results to Polarion")
    parser.add_argument('--password',
                        help="Password to use to submit results to Polarion")
    parser.add_argument('--msgbus-user',
                        help="Username to use to connect to the message bus")
    parser.add_argument('--msgbus-password',
                        help="Password to use to connect to the message bus")
    parser.add_argument('-f', '--force', action='store_true',
                        help="Don't validate test run id")
    parser.add_argument('--no-verify', action='store_true',
                        help="Don't verify results submission")
    parser.add_argument('--verify-timeout', type=int, default=300, metavar='SEC',
                        help="How long to wait (in seconds) for verification of results submission"
                             " (default: %(default)s)")
    parser.add_argument('--msgbus-log',
                        help="Where to save the log file returned by msgbus (default: not saved)")
    parser.add_argument('--log-level',
                        help="Set logging to specified level")
    return parser.parse_args(args)


def init_log(log_level):
    """Initializes logging."""
    log_level = log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))


def get_testrun_id(args, testrun_id):
    """Returns testrun id."""
    if (args.testrun_id and testrun_id and not args.force and
            testrun_id != args.testrun_id):
        raise Dump2PolarionException(
            "The test run id '{}' found in exported data doesn't match '{}'. "
            "If you really want to proceed, add '-f'.".format(testrun_id, args.testrun_id))

    found_testrun_id = args.testrun_id or testrun_id
    if not found_testrun_id:
        raise Dump2PolarionException(
            "The testrun id was not specified on command line and not found in the input data.")

    return found_testrun_id


# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
def main(args=None):
    """Main function for cli."""
    args = get_args(args)

    init_log(args.log_level)

    try:
        config = get_config(args.config_file, args=vars(args))
    except Dump2PolarionException as err:
        logger.fatal(err)
        return 1

    # select importer based on input file type and load needed tools
    _, ext = os.path.splitext(args.input_file)
    ext = ext.lower()
    if 'ostriz' in args.input_file:
        from dump2polarion import ostriztools
        importer = ostriztools.import_ostriz
    elif ext == '.xml':
        with io.open(args.input_file, encoding='utf-8') as input_file:
            xml = input_file.read()

        if '<testsuites' in xml or '<testcases' in xml:
            if args.no_submit:
                logger.info("Nothing to do")
                return 0
            # expect importer xml and just submit it
            response = submit_and_verify(xml, config=config, **vars(args))
            return 0 if response else 2

        # expect junit-report from pytest
        from dump2polarion import junittools
        del xml
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
        testrun_id = get_testrun_id(args, records.testrun)
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
        response = submit_and_verify(output, config=config, **vars(args))

        if importer is dbtools.import_sqlite and response:
            dbtools.mark_exported_sqlite(args.input_file, import_time)

        return 0 if response else 2
