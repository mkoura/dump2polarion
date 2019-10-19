"""Helper functions for handling data in pytest junit format."""

import os

from lxml import etree

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.exporters import xunit_exporter

_PARAMETER_PREFIX = "polarion-parameter-"


def _get_xml_root(junit_file):
    try:
        tree = etree.parse(os.path.expanduser(junit_file))
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(junit_file, err))

    return tree.getroot()


def _parse_testcase_record(testcase_record):
    """Parse testcase record and return it's info."""
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
    """Extract parameters from properties."""
    new_properties = {}
    parameters = {}
    for key, value in properties.items():
        if key.startswith(_PARAMETER_PREFIX):
            parameters[key.replace(_PARAMETER_PREFIX, "")] = value
        else:
            new_properties[key] = value

    return new_properties, parameters


# pylint: disable=unused-argument,too-many-locals
def import_junit(junit_file, **kwargs):
    """Read the content of the junit-results file produced by pytest and return imported data."""
    xml_root = _get_xml_root(junit_file)

    testcases = xml_root.xpath(".//testcase")
    if testcases is None:
        testcases = ()

    results = []
    for test_data in testcases:
        verdict, comment, properties = _parse_testcase_record(test_data)
        properties, parameters = _extract_parameters_from_properties(properties)

        testcase_id = properties.get("polarion-testcase-id")
        title = test_data.get("name")
        classname = test_data.get("classname")
        time = test_data.get("time", 0)
        filepath = test_data.get("file")

        data = {
            "id": testcase_id,
            "title": title,
            "classname": classname,
            "verdict": verdict,
            "comment": comment,
            "time": time,
            "file": filepath,
        }
        for key, value in properties.items():
            data[key] = value
        if parameters:
            data["params"] = utils.sorted_dict(parameters)

        results.append(utils.sorted_dict(data))

    return xunit_exporter.ImportedData(results=results, testrun=None)
