# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Helper functions for handling data in pytest junit format.
"""

from __future__ import absolute_import, unicode_literals

import os

from collections import OrderedDict

from xml.etree import ElementTree

from dump2polarion import exporter
from dump2polarion.exceptions import Dump2PolarionException


def _get_xml_root(junit_file):
    try:
        tree = ElementTree.parse(os.path.expanduser(junit_file))
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(junit_file, err))

    return tree.getroot()


def _parse_testcase_record(testcase_record):
    """Parses testcase record and returns it's info."""
    verdict = None
    verdict_found = False
    comment = ''
    properties = {}
    for element in testcase_record:
        if not verdict_found:
            if element.tag == 'error':
                verdict = 'failed'
                comment = element.get('message')
                # continue to see if there's more telling verdict for this record
            elif element.tag == 'failure':
                verdict = 'failed'
                comment = element.get('message')
                verdict_found = True
            elif element.tag == 'skipped':
                verdict = 'skipped'
                comment = element.get('message')
                verdict_found = True
        if element.tag == 'properties':
            for prop in element:
                properties[prop.get('name')] = prop.get('value')
    if not verdict:
        verdict = 'passed'

    return verdict, comment, properties


# pylint: disable=unused-argument
def import_junit(junit_file, **kwargs):
    """Reads the content of the junit-results file produced by pytest and returns imported data."""
    xml_root = _get_xml_root(junit_file)

    results = []
    for test_data in xml_root:
        if test_data.tag != 'testcase':
            continue

        verdict, comment, properties = _parse_testcase_record(test_data)

        title = test_data.get('name')
        classname = test_data.get('classname')
        time = test_data.get('time', 0)
        filepath = test_data.get('file')

        data = [
            ('title', title),
            ('classname', classname),
            ('verdict', verdict),
            ('comment', comment),
            ('time', time),
            ('file', filepath),
        ]
        for key in properties:
            data.append((key, properties[key]))

        results.append(OrderedDict(data))

    return exporter.ImportedData(results=results, testrun=None)
