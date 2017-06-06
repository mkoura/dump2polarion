# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Helper functions for handling data in pytest junit format.
"""

from __future__ import unicode_literals, absolute_import

import os

from collections import OrderedDict

from xml.etree import ElementTree

from dump2polarion import ImportedData
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

        verdict = 'failed'
        comment = ''
        for element in test_data:
            # we don't want to submit errors and failures anyway
            if element.tag in ('error', 'failure'):
                break
            elif element.tag == 'skipped':
                comment = element.get('message')
                if comment:
                    verdict = 'skipped'
                break
        else:
            verdict = 'passed'

        if verdict == 'failed':
            continue

        title = test_data.get('name')
        classname = test_data.get('classname')
        time = test_data.get('time', 0)

        record = OrderedDict([
            ('title', title),
            ('classname', classname),
            ('verdict', verdict),
            ('comment', comment),
            ('time', time)])
        results.append(record)

    return ImportedData(results=results, testrun=None)
