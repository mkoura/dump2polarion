# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Helper functions for handling data in pytest junit format.
"""

from __future__ import unicode_literals, absolute_import

import os

from collections import OrderedDict

from xml.etree import ElementTree

from dump2polarion.exporter import ImportedData
from dump2polarion.exceptions import Dump2PolarionException


# pylint: disable=unused-argument
def import_junit(junit_file, **kwargs):
    """Reads the content of the junit-results file produced by pytest and returns imported data."""
    try:
        tree = ElementTree.parse(os.path.expanduser(junit_file))
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(junit_file, err))
    xml_root = tree.getroot()

    results = []
    for test_data in xml_root:
        if test_data.tag != 'testcase':
            continue

        verdict = None
        comment = ''
        for element in test_data:
            if element.tag == 'error':
                verdict = 'failed'
                comment = element.get('message')
                # continue to see if there's more telling verdict for this record
            elif element.tag == 'failure':
                verdict = 'failed'
                comment = element.get('message')
                break
            elif element.tag == 'skipped':
                verdict = 'skipped'
                comment = element.get('message')
                break
        if not verdict:
            verdict = 'passed'

        title = test_data.get('name')
        classname = test_data.get('classname')
        time = test_data.get('time', 0)
        filepath = test_data.get('file')

        record = OrderedDict([
            ('title', title),
            ('classname', classname),
            ('verdict', verdict),
            ('comment', comment),
            ('time', time),
            ('file', filepath),
        ])
        results.append(record)

    return ImportedData(results=results, testrun=None)
