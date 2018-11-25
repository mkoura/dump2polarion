# -*- coding: utf-8 -*-
"""
Helper functions for handling data in pytest junit format.
"""

from __future__ import absolute_import, unicode_literals

import os
from collections import OrderedDict

import six
from lxml import etree

from dump2polarion import xunit_exporter
from dump2polarion.exceptions import Dump2PolarionException

_PARAMETER_PREFIX = "polarion-parameter-"


def _get_xml_root(junit_file):
    try:
        tree = etree.parse(os.path.expanduser(junit_file))
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(junit_file, err))

    return tree.getroot()


def _parse_testcase_record(testcase_record):
    """Parses testcase record and returns it's info."""
    verdict = None
    verdict_found = False
    comment = ""
    properties = {}
    for element in testcase_record:
        if not verdict_found:
            if element.tag == "error":
                verdict = "failed"
                comment = element.get("message")
                # continue to see if there's more telling verdict for this record
            elif element.tag == "failure":
                verdict = "failed"
                comment = element.get("message")
                verdict_found = True
            elif element.tag == "skipped":
                verdict = "skipped"
                comment = element.get("message")
                verdict_found = True
        if element.tag == "properties":
            for prop in element:
                properties[prop.get("name")] = prop.get("value")
    if not verdict:
        verdict = "passed"

    return verdict, comment, properties


def _extract_parameters_from_properties(properties):
    """Extracts parameters from properties."""
    new_properties = {}
    parameters = []
    for key, value in six.iteritems(properties):
        if key.startswith(_PARAMETER_PREFIX):
            parameters.append((key.replace(_PARAMETER_PREFIX, ""), value))
        else:
            new_properties[key] = value

    return new_properties, sorted(parameters)


# pylint: disable=unused-argument
def import_junit(junit_file, **kwargs):
    """Reads the content of the junit-results file produced by pytest and returns imported data."""
    xml_root = _get_xml_root(junit_file)

    results = []
    for test_data in xml_root:
        if test_data.tag != "testcase":
            continue

        verdict, comment, properties = _parse_testcase_record(test_data)
        properties, parameters = _extract_parameters_from_properties(properties)

        title = test_data.get("name")
        classname = test_data.get("classname")
        time = test_data.get("time", 0)
        filepath = test_data.get("file")

        data = [
            ("title", title),
            ("classname", classname),
            ("verdict", verdict),
            ("comment", comment),
            ("time", time),
            ("file", filepath),
        ]
        for key in sorted(properties):
            data.append((key, properties[key]))
        if parameters:
            data.append(("params", OrderedDict(parameters)))

        results.append(OrderedDict(data))

    return xunit_exporter.ImportedData(results=results, testrun=None)
