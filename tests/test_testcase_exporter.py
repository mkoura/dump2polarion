# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import copy
import io
import os
from collections import OrderedDict

import pytest

from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters.testcases_exporter import TestcaseExport
from tests import conf

REQ_DATA = [
    OrderedDict(
        (
            ("id", "ITEM01"),
            ("title", "test_manual"),
            ("description", "Manual tests with many supported fields."),
            ("approver-ids", "mkourim:approved"),
            ("assignee-id", "mkourim"),
            ("due-date", "2018-09-30"),
            ("initial-estimate", "1/4h"),
            ("caseautomation", "manualonly"),
            ("caseimportance", "high"),
            ("caselevel", 2),
            ("caseposneg", "positive"),
            ("testtype", "functional"),
            ("subtype1", "-"),
            ("subtype2", "-"),
            ("upstream", "yes"),
            ("tags", "tag1, tag2"),
            ("setup", "Do this first"),
            ("teardown", "Clean up"),
            ("automation_script", "file#L83"),
            ("testSteps", ["step1", "step2"]),
            ("expectedResults", ["result1", "result2"]),
            ("linked-items", "ITEM01"),
            ("unknown", "non-included"),
        )
    ),
    OrderedDict(
        (
            ("title", "test_minimal_param"),
            ("params", ["param1", "param2"]),
            ("linked-items-lookup-method", "name"),
            ("linked-items", [{"id": "ITEM01", "role": "derived_from"}]),
        )
    ),
]


@pytest.fixture(scope="module")
def config_cloudtp(config_prop):
    cloudtp = copy.deepcopy(config_prop)
    cloudtp["polarion-project-id"] = "CLOUDTP"
    cloudtp["testcase_import_properties"] = {"prop1": "val1", "prop2": "val2"}
    return cloudtp


@pytest.fixture(scope="module")
def config_with_fields(config_prop):
    config_fields = copy.deepcopy(config_prop)
    config_fields["default_fields"] = {"caseimportance": "medium", "startsin": "5.10"}
    config_fields["custom_fields"] = ["caseimportance", "startsin", "testtype"]
    return config_fields


class TestTestcase(object):
    def test_export_cloudtp(self, config_cloudtp):
        testcase_exp = TestcaseExport(REQ_DATA, config_cloudtp)
        complete = testcase_exp.export()
        fname = "testcase_complete_cloudtp.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_export_cfme(self, config_prop):
        testcase_exp = TestcaseExport(REQ_DATA, config_prop)
        complete = testcase_exp.export()
        fname = "testcase_complete_cfme.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_export_fields_cfme(self, config_with_fields):
        testcase_exp = TestcaseExport(REQ_DATA, config_with_fields)
        complete = testcase_exp.export()
        fname = "testcase_fields_cfme.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_export_cfme_params(self, config_prop):
        new_config = copy.deepcopy(config_prop)
        new_config["cfme_parametrize"] = True
        testcase_exp = TestcaseExport(REQ_DATA, new_config)
        complete = testcase_exp.export()
        fname = "testcase_complete_cfme_param.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_invalid_lookup(self, config_cloudtp):
        new_config = copy.deepcopy(config_cloudtp)
        new_config["testcase_import_properties"] = {"lookup-method": "inv"}
        testcase_exp = TestcaseExport(REQ_DATA, new_config)
        with pytest.raises(Dump2PolarionException) as excinfo:
            testcase_exp.export()
        assert "Invalid value 'inv' for the 'lookup-method' property" in str(excinfo.value)

    def test_no_requirements(self, config_cloudtp):
        testcase_exp = TestcaseExport([], config_cloudtp)
        with pytest.raises(NothingToDoException) as excinfo:
            testcase_exp.export()
        assert "Nothing to export" in str(excinfo.value)
