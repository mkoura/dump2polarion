# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import copy
import io
import os

import pytest
from lxml import etree

from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.importer import do_import
from dump2polarion.utils import get_unicode_str
from dump2polarion.xunit_exporter import ImportedData, XunitExport
from tests import conf


@pytest.fixture(scope="module")
def records_ids():
    csv_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
    return do_import(csv_file)


@pytest.fixture(scope="module")
def records_names():
    csv_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
    records = do_import(csv_file)
    for res in records.results:
        res.pop("id")
    return records


def test_top_element(config_prop, records_ids):
    exporter = XunitExport("5_8_0_17", records_ids, config_prop, transform_func=lambda: None)
    top_element = exporter._top_element()
    parsed = "<testsuites><!--Generated for testrun 5_8_0_17--></testsuites>".strip()
    top_element_str = get_unicode_str(etree.tostring(top_element, encoding="utf-8").strip())
    assert top_element_str == parsed


class TestProperties(object):
    def test_properties_element(self, config_prop, records_ids):
        exporter = XunitExport("5_8_0_17", records_ids, config_prop, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        parsed = (
            "<properties>"
            '<property name="polarion-testrun-id" value="5_8_0_17"/>'
            '<property name="polarion-project-id" value="RHCF3"/>'
            '<property name="polarion-dry-run" value="False"/>'
            '<property name="polarion-response-test" value="test"/>'
            '<property name="polarion-testrun-status-id" value="inprogress"/>'
            "</properties>".strip()
        )
        properties_str = get_unicode_str(
            etree.tostring(properties_element, encoding="utf-8").strip()
        )
        assert properties_str == parsed

    def test_properties_lookup_config(self, config_prop, records_names):
        new_config = copy.deepcopy(config_prop)
        new_config["xunit_import_properties"]["polarion-lookup-method"] = "id"
        exporter = XunitExport("5_8_0_17", records_names, new_config, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        exporter._fill_lookup_prop(properties_element)
        properties_str = get_unicode_str(
            etree.tostring(properties_element, encoding="utf-8").strip()
        )
        assert '<property name="polarion-lookup-method" value="id"/>' in properties_str

    def test_properties_invalid_lookup(self, config_prop, records_ids):
        new_config = copy.deepcopy(config_prop)
        new_config["xunit_import_properties"]["polarion-lookup-method"] = "invalid"
        exporter = XunitExport("5_8_0_17", records_ids, new_config)
        with pytest.raises(Dump2PolarionException) as excinfo:
            exporter.export()
        assert "Invalid value 'invalid' for the 'polarion-lookup-method'" in str(excinfo.value)


class TestE2E(object):
    def test_e2e_noresults(self, config_prop, records_ids):
        exporter = XunitExport(
            "5_8_0_17", records_ids, config_prop, transform_func=lambda arg: None
        )
        with pytest.raises(NothingToDoException) as excinfo:
            exporter.export()
        assert "Nothing to export" in str(excinfo.value)

    def test_e2e_missing_results(self, config_prop):
        new_records = ImportedData(results=[], testrun=None)
        exporter = XunitExport(
            "5_8_0_17", new_records, config_prop, transform_func=lambda arg: None
        )
        with pytest.raises(NothingToDoException) as excinfo:
            exporter._fill_tests_results(None)
        assert "Nothing to export" in str(excinfo.value)

    def test_e2e_ids_notransform(self, config_prop, records_ids):
        exporter = XunitExport("5_8_0_17", records_ids, config_prop, transform_func=lambda arg: arg)
        complete = exporter.export()
        fname = "complete_notransform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_transform(self, config_prop, records_ids):
        exporter = XunitExport("5_8_0_17", records_ids, config_prop)
        complete = exporter.export()
        fname = "complete_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_names_notransform(self, config_prop, records_names):
        exporter = XunitExport(
            "5_8_0_17", records_names, config_prop, transform_func=lambda arg: arg
        )
        complete = exporter.export()
        fname = "complete_notransform_name.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_names_transform(self, config_prop, records_names):
        exporter = XunitExport("5_8_0_17", records_names, config_prop)
        complete = exporter.export()
        fname = "complete_transform_name.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
