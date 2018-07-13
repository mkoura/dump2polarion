# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import io
import os

import pytest
from mock import Mock, patch

from dump2polarion import ostriztools
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.xunit_exporter import XunitExport
from tests import conf


@pytest.fixture(scope="module")
def records_json():
    json_file = os.path.join(conf.DATA_PATH, "ostriz.json")
    return ostriztools.import_ostriz(json_file)


@pytest.fixture(scope="module")
def records_json_cmp():
    json_file = os.path.join(conf.DATA_PATH, "ostriz_cmp.json")
    return ostriztools.import_ostriz(json_file)


@pytest.fixture(scope="module")
def records_json_search():
    json_file = os.path.join(conf.DATA_PATH, "ostriz_search.json")
    return ostriztools.import_ostriz(json_file)


class TestOstriz(object):
    def test_testrun_id_simple(self):
        testrun_id = ostriztools._get_testrun_id("5.8.0.17")
        assert testrun_id == "5_8_0_17"

    def test_testrun_id_build(self):
        testrun_id = ostriztools._get_testrun_id("5.8.0.17-20170525183055_6317a22")
        assert testrun_id == "5_8_0_17"

    def test_testrun_id_fill(self):
        testrun_id = ostriztools._get_testrun_id("5.8.0.7-2017")
        assert testrun_id == "5_8_0_07"

    def test_testrun_id_invalid(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            ostriztools._get_testrun_id("INVALID")
        assert "Cannot find testrun id" in str(excinfo.value)

    def test_duration_good(self):
        duration = ostriztools._calculate_duration(1495766591.151192, 1495768544.573208)
        assert duration == 1953.422016

    def test_duration_bad_finish(self):
        duration = ostriztools._calculate_duration(1495766591.151192, None)
        assert duration == 0

    def test_duration_bad_start(self):
        duration = ostriztools._calculate_duration(0, 1495768544.573208)
        assert duration == 0

    def test_import_orig_data(self, records_json):
        assert hasattr(records_json, "results")
        assert len(records_json.results) == 6
        assert "title" in records_json.results[0]
        assert hasattr(records_json, "testrun")
        assert records_json.testrun == "5_8_0_17"

    def test_invalid_json(self):
        fname = "junit-report.xml"
        with pytest.raises(Dump2PolarionException) as excinfo:
            ostriztools.import_ostriz(os.path.join(conf.DATA_PATH, fname))
        assert "Failed to parse JSON" in str(excinfo.value)

    def test_remote_invalid_json(self):
        with patch("requests.get", return_value=False):
            with pytest.raises(Dump2PolarionException) as excinfo:
                ostriztools.import_ostriz("https://foo")
        assert "Failed to parse JSON" in str(excinfo.value)

    def test_remote_json(self, records_json):
        json_file = os.path.join(conf.DATA_PATH, "ostriz.json")
        with io.open(json_file, encoding="utf-8") as input_json:
            parsed = input_json.read()
        retval = Mock()
        retval.text = parsed
        with patch("requests.get", return_value=retval):
            loaded_json = ostriztools.import_ostriz("https://foo")
        assert loaded_json == records_json

    def test_no_json(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            ostriztools.import_ostriz("NONEXISTENT.json")
        assert "Invalid location" in str(excinfo.value)

    def test_empty_json(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            ostriztools._parse_ostriz("")
        assert "No data to import" in str(excinfo.value)

    def test_e2e_ids_notransform(self, config_prop, records_json):
        exporter = XunitExport(
            "5_8_0_17", records_json, config_prop, transform_func=lambda arg: arg
        )
        complete = exporter.export()
        fname = "ostriz_notransform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_transform(self, config_prop, records_json):
        exporter = XunitExport("5_8_0_17", records_json, config_prop)
        complete = exporter.export()
        fname = "ostriz_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_cmp_ids_transform(self, config_prop_cmp, records_json_cmp):
        exporter = XunitExport("5_8_0_17", records_json_cmp, config_prop_cmp)
        complete = exporter.export()
        fname = "ostriz_transform_cmp.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_search_transform(self, config_prop, records_json_search):
        exporter = XunitExport("5_8_0_17", records_json_search, config_prop)
        complete = exporter.export()
        fname = "ostriz_search_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
