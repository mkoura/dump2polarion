# -*- coding: utf-8 -*-
"""
Dump testcases results from a CSV, SQLite, junit, JSON or Ostriz input file to XUnit file.
Submit XUnit, Testcases or Requirements XML to the Polarion Importers.
"""

from __future__ import absolute_import, unicode_literals

import argparse
import datetime
import io
import logging
import os

import dump2polarion
from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.results import dbtools

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_args(args=None):
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description="dump2polarion")
    parser.add_argument(
        "-i",
        "--input_file",
        required=True,
        help="Path to CSV, SQLite or JUnit reports file or importers XML file",
    )
    parser.add_argument(
        "-o", "--output_file", help="Where to save the XML output file (default: not saved)"
    )
    parser.add_argument("-t", "--testrun-id", help="Polarion test run id")
    parser.add_argument("-c", "--config-file", help="Path to config YAML")
    parser.add_argument(
        "-n", "--no-submit", action="store_true", help="Don't submit results to Polarion"
    )
    parser.add_argument("--user", help="Username to use to submit results to Polarion")
    parser.add_argument("--password", help="Password to use to submit results to Polarion")
    parser.add_argument("--polarion-url", help="Base Polarion URL")
    parser.add_argument("-f", "--force", action="store_true", help="Don't validate test run id")
    parser.add_argument("--dry-run", action="store_true", help="Dry run, don't update anything")
    parser.add_argument("--no-verify", action="store_true", help="Don't verify import success")
    parser.add_argument(
        "--verify-timeout",
        type=int,
        default=300,
        metavar="SEC",
        help="How long to wait (in seconds) for verification of results submission"
        " (default: %(default)s)",
    )
    parser.add_argument(
        "--job-log", help="Where to save the log file produced by the Importer (default: not saved)"
    )
    parser.add_argument("--log-level", help="Set logging to specified level")
    return parser.parse_args(args)


def get_submit_args(args):
    """Gets arguments for the `submit_and_verify` method."""
    submit_args = dict(
        testrun_id=args.testrun_id,
        user=args.user,
        password=args.password,
        no_verify=args.no_verify,
        verify_timeout=args.verify_timeout,
        log_file=args.job_log,
        dry_run=args.dry_run,
    )
    return {k: v for k, v in submit_args.items() if v is not None}


def get_testrun_id(args, config, records_testrun_id):
    """Returns testrun id."""
    config_testrun_id = utils.get_testrun_id_config(config)

    found_testrun_id = args.testrun_id or records_testrun_id or config_testrun_id
    if not found_testrun_id:
        raise Dump2PolarionException(
            "The testrun id was not specified on command line and not found in the input data "
            "or config file."
        )

    match = True
    for tr_id in (args.testrun_id, records_testrun_id, config_testrun_id):
        if tr_id and tr_id != found_testrun_id:
            match = False
            break

    if not match and args.force:
        logger.warning("Using '%s' as testrun id.", found_testrun_id)
    elif not match:
        raise Dump2PolarionException(
            "The test run ids found in exported data, config file and/or specified on command line "
            "differ. If you really want to proceed, add '-f' and test run id '{}' "
            "will be used.".format(found_testrun_id)
        )

    return found_testrun_id


def submit_if_ready(args, submit_args, config):
    """Submits the input XML file if it's already in the expected format."""
    __, ext = os.path.splitext(args.input_file)
    if ext.lower() != ".xml":
        return None

    with io.open(args.input_file, encoding="utf-8") as input_file:
        xml = input_file.read(1024)

    if not ("<testsuites" in xml or "<testcases" in xml or "<requirements" in xml):
        return None

    if args.no_submit:
        logger.info("Nothing to do")
        return 0

    # expect importer xml and just submit it
    response = dump2polarion.submit_and_verify(
        xml_file=args.input_file, config=config, **submit_args
    )
    return 0 if response else 2


def _get_config(args):
    args_config = {}
    if args.polarion_url:
        args_config["polarion_url"] = args.polarion_url

    return dump2polarion.get_config(args.config_file, args_config)


def dumper(args, config, transform_func=None):
    """Dumper main function."""
    submit_args = get_submit_args(args)

    submit_outcome = submit_if_ready(args, submit_args, config)
    if submit_outcome is not None:
        # submitted, nothing more to do
        return submit_outcome

    import_time = datetime.datetime.utcnow()

    try:
        records = dump2polarion.import_results(args.input_file, older_than=import_time)
        testrun_id = get_testrun_id(args, config, records.testrun)
        exporter = dump2polarion.XunitExport(
            testrun_id, records, config, transform_func=transform_func
        )
        output = exporter.export()
    except NothingToDoException as info:
        logger.info(info)
        return 0
    except (EnvironmentError, Dump2PolarionException) as err:
        logger.fatal(err)
        return 1

    if args.output_file or args.no_submit:
        # when no output file is specified, the 'testrun_TESTRUN_ID-TIMESTAMP'
        # file will be created in current directory
        exporter.write_xml(output, args.output_file)

    if not args.no_submit:
        response = dump2polarion.submit_and_verify(output, config=config, **submit_args)

        __, ext = os.path.splitext(args.input_file)
        if ext.lower() in dbtools.SQLITE_EXT and response:
            dbtools.mark_exported_sqlite(args.input_file, import_time)

        return 0 if response else 2

    return 0


def main(args=None, transform_func=None):
    """Main function for cli."""
    args = get_args(args)

    utils.init_log(args.log_level)

    try:
        config = _get_config(args)
    except Dump2PolarionException as err:
        logger.fatal(err)
        return 1

    return dumper(args, config, transform_func=transform_func)
