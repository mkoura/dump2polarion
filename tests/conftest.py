# encoding: utf-8
# pylint: disable=missing-docstring,no-self-use

from __future__ import unicode_literals

import copy
import io
import logging
import os
from collections import OrderedDict

import pytest

from tests import conf

GENERIC_CONF = {
    "xunit_target": "https://polarion.example.com/import/xunit",
    "testcase_taget": "https://polarion.example.com/import/testcase",
    "requirement_target": "https://polarion.example.com/import/requirement",
    "xunit_queue": "https://polarion.example.com/import/xunit-queue",
    "testcase_queue": "https://polarion.example.com/import/testcase-queue",
    "requirement_queue": "https://polarion.example.com/import/requirement-queue",
    "repo_address": "https://foo/bar/baz",
    "cfme_run_id": "id123",
}


VALID_CASELEVELS = {
    "valid_values": {"caselevel": ["component", "integration", "system", "acceptance"]}
}

RHCF3_XUNIT_PROPS = OrderedDict(
    (
        ("polarion-dry-run", False),
        ("polarion-testrun-status-id", "inprogress"),
        ("polarion-response-test", "test"),
    )
)

POLARION_DEFAULT_FIELDS = OrderedDict(
    (
        ("assignee", ""),
        ("casecomponent", ""),
        ("initialEstimate", "1m"),
        ("caseimportance", "high"),
        ("caselevel", "component"),
        ("caseposneg", "positive"),
        ("caseautomation", "automated"),
        ("testtype", "functional"),
        ("subtype1", "-"),
        ("subtype2", "-"),
        ("tags", ""),
        ("setup", ""),
        ("teardown", ""),
        ("description", ""),
        ("linkedWorkItems", ""),
        ("testSteps", ""),
        ("expectedResults", ""),
        ("title", ""),
        ("work_item_id", ""),
    )
)

RHCF3_TESTCASE_PROPS = OrderedDict((("lookup-method", "name"),))

RHCF3_CONF = GENERIC_CONF.copy()
RHCF3_CONF["polarion-project-id"] = "RHCF3"
RHCF3_CONF["xunit_import_properties"] = RHCF3_XUNIT_PROPS
RHCF3_CONF["testcase_import_properties"] = RHCF3_TESTCASE_PROPS
RHCF3_CONF["default_fields"] = POLARION_DEFAULT_FIELDS
RHCF3_CONF["docstrings"] = VALID_CASELEVELS

CMP_CONF = GENERIC_CONF.copy()
CMP_CONF["polarion-project-id"] = "CMP"
CMP_CONF["xunit_import_properties"] = RHCF3_XUNIT_PROPS.copy()
CMP_CONF["default_fields"] = POLARION_DEFAULT_FIELDS.copy()
CMP_CONF["docstrings"] = VALID_CASELEVELS.copy()


@pytest.fixture(scope="session")
def config_prop():
    return copy.deepcopy(RHCF3_CONF)


@pytest.fixture(scope="session")
def config_prop_cmp():
    return copy.deepcopy(CMP_CONF)


@pytest.fixture(scope="function")
def config_e2e():
    conf_file = os.path.join(conf.DATA_PATH, "polarion_tools.yaml")
    return str(conf_file)


class SimpleFormatter(object):
    def format(self, record):
        message = record.getMessage()
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return message


@pytest.yield_fixture
def captured_log():
    buff = io.StringIO()
    handler = logging.StreamHandler(buff)
    handler.setFormatter(SimpleFormatter())

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield buff

    logger.handlers.remove(handler)
