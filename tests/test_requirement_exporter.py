# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import copy
import io
import os
from collections import OrderedDict

import pytest

from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.requirements_exporter import RequirementExport
from tests import conf

REQ_DATA = [
    OrderedDict(
        (
            ("title", "req01"),
            ("approver-ids", "sbulage:approved"),
            ("assignee-id", "mkourim"),
            ("category-ids", "CAT-01"),
            ("due-date", "2018-05-30"),
            ("planned-in-ids", "PROJ-01"),
            ("initial-estimate", "1/4h"),
            ("priority-id", "medium"),
            ("severity-id", "good_to_have"),
            ("status-id", "STAT-01"),
            ("reqtype", "functional"),
        )
    ),
    OrderedDict(
        (
            ("title", "req02"),
            ("description", "requirement description"),
            ("assignee-id", "mkourim"),
            ("initial-estimate", "1/4h"),
        )
    ),
    OrderedDict((("id", "PROJ-01"), ("title", "req03"), ("initial-estimate", None))),
    OrderedDict((("id", "PROJ-02"),)),
]


@pytest.fixture(scope="module")
def config_cloudtp(config_prop):
    config_prop["polarion-project-id"] = "CLOUDTP"
    config_prop["requirements-document-relative-path"] = "testing/requirements"
    config_prop["requirements_import_properties"] = {"prop1": "val1", "prop2": "val2"}
    return config_prop


class TestRequirement(object):
    def test_export(self, config_cloudtp):
        req_exp = RequirementExport(REQ_DATA, config_cloudtp)
        complete = req_exp.export()
        fname = "requirement_complete.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_invalid_lookup(self, config_cloudtp):
        new_config = copy.deepcopy(config_cloudtp)
        new_config["requirements_import_properties"] = {"lookup-method": "inv"}
        req_exp = RequirementExport(REQ_DATA, new_config)
        with pytest.raises(Dump2PolarionException) as excinfo:
            req_exp.export()
        assert "Invalid value 'inv' for the 'lookup-method' property" in str(excinfo.value)

    def test_no_requirements(self, config_cloudtp):
        req_exp = RequirementExport([], config_cloudtp)
        with pytest.raises(NothingToDoException) as excinfo:
            req_exp.export()
        assert "Nothing to export" in str(excinfo.value)
