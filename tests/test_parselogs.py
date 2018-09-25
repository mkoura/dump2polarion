# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os

import pytest

from dump2polarion import parselogs
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf


class TestParselog(object):
    def test_xunit_name(self):
        log_file = os.path.join(conf.DATA_PATH, "xunit.log")
        parsed_log = parselogs.parse(log_file)
        assert parsed_log.log_type == "xunit"
        assert len(parsed_log.duplicate_items) == 10
        assert len(parsed_log.existing_items) == 291
        assert len(parsed_log.new_items) == 26
        eitem = parsed_log.existing_items[10]
        assert eitem.id == "RHCF3-47696"
        assert eitem.name == "test_collections_actions[virtualcenter-users]"
        assert not eitem.custom_id

    def test_xunit_custom_id(self):
        log_file = os.path.join(conf.DATA_PATH, "xunit_vmaas.log")
        parsed_log = parselogs.parse(log_file)
        assert parsed_log.log_type == "xunit"
        assert not parsed_log.duplicate_items
        assert not parsed_log.new_items
        assert len(parsed_log.existing_items) == 168
        eitem = parsed_log.existing_items[10]
        assert eitem.id == "INSI-1547"
        assert eitem.name == "TestUpdateInOtherRepo.test_post_single"
        assert eitem.custom_id == "4267c8b00cf1f4d48c9565aa166c318e"

    def test_xunit_invalid(self):
        with pytest.raises(Dump2PolarionException):
            parselogs.parse_xunit([], "empty")

    def test_testcase_custom_id(self):
        log_file = os.path.join(conf.DATA_PATH, "testcase.log")
        parsed_log = parselogs.parse(log_file)
        assert parsed_log.log_type == "testcase"
        assert not parsed_log.new_items
        assert len(parsed_log.duplicate_items) == 1
        assert len(parsed_log.existing_items) == 82
        eitem = parsed_log.existing_items[10]
        assert eitem.id == "INSI-1498"
        assert eitem.name == "TestCVEsCorrect.test_post_single_smoke"
        assert eitem.custom_id == "0422b43ddc9ccc44f2cc5358ac25ba58"

    def test_testcase_invalid(self):
        with pytest.raises(Dump2PolarionException):
            parselogs.parse_testcase([], "empty")

    def test_requirement_name(self):
        log_file = os.path.join(conf.DATA_PATH, "requirements.log")
        parsed_log = parselogs.parse(log_file)
        assert parsed_log.log_type == "requirement"
        assert len(parsed_log.duplicate_items) == 1
        assert len(parsed_log.new_items) == 49
        assert len(parsed_log.existing_items) == 1
        eitem = parsed_log.new_items[10]
        assert eitem.id == "INSI-1683"
        assert eitem.name == "configuration"
        assert not eitem.custom_id

    def test_requirement_invalid(self):
        with pytest.raises(Dump2PolarionException):
            parselogs.parse_requirements([], "empty")

    def test_log_invalid(self, tmpdir):
        invalid_log = os.path.join(str(tmpdir), "invalid.log")
        with open(invalid_log, "w") as output_file:
            output_file.write("foo\n")
        with pytest.raises(Dump2PolarionException):
            parselogs.parse(invalid_log)
