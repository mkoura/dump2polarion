#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results from a CSV input file to xunit file and submit it
to Polarion® xunit importer.
"""

import argparse
import logging
import dump2polarion


def get_args():
    """Get command line arguments."""
    parser = argparse.ArgumentParser(description='CSV Importer')
    parser.add_argument('-i', '--input_file', required=True, action='store',
                        help="Path to CSV results file")
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
    return parser.parse_args()


def main():
    """Main function for cli."""
    args = get_args()
    config = dump2polarion.get_config(args.config_file)
    tests_results = dump2polarion.import_csv(args.input_file)

    exporter = dump2polarion.XunitExport(args.testrun_id, tests_results, config)
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
