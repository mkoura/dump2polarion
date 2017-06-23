# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os
import copy
import io

from xml.etree import ElementTree

import pytest
from tests import conf

from dump2polarion.exporter import XunitExport
from dump2polarion.importer import do_import
from dump2polarion.exceptions import Dump2PolarionException


@pytest.fixture(scope="module")
def records_ids():
    csv_file = os.path.join(conf.DATA_PATH, 'workitems_ids.csv')
    return do_import(csv_file)


@pytest.fixture(scope="module")
def records_names():
    csv_file = os.path.join(conf.DATA_PATH, 'workitems_ids.csv')
    records = do_import(csv_file)
    for res in records.results:
        res.pop('id')
    return records


def test_top_element(config_prop, records_ids):
    exporter = XunitExport('5_8_0_17', records_ids, config_prop, transform_func=lambda: None)
    top_element = exporter._top_element()
    parsed = '<testsuites><!--Generated for testrun 5_8_0_17--></testsuites>'.strip()
    assert ElementTree.tostring(top_element, 'utf-8').strip() == parsed


class TestProperties(object):
    def test_properties_element(self, config_prop, records_ids):
        exporter = XunitExport(
            '5_8_0_17', records_ids, config_prop, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        parsed = ('<properties>'
                  '<property name="polarion-testrun-id" value="5_8_0_17" />'
                  '<property name="polarion-dry-run" value="False" />'
                  '<property name="polarion-testrun-status-id" value="inprogress" />'
                  '<property name="polarion-response-test" value="test" />'
                  '<property name="polarion-project-id" value="RHCF3" />'
                  '<property name="polarion-lookup-method" value="ID" />'
                  '</properties>'.strip())
        assert ElementTree.tostring(properties_element, 'utf-8').strip() == parsed

    def test_properties_response(self, config_prop, records_ids):
        new_config = copy.deepcopy(config_prop)
        del new_config['xunit_import_properties']['polarion-response-test']
        exporter = XunitExport('5_8_0_17', records_ids, new_config, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        assert '<property name="polarion-response-dump2polarion" value=' in ElementTree.tostring(
            properties_element, 'utf-8').strip()

    def test_properties_lookup_name(self, config_prop, records_names):
        exporter = XunitExport(
            '5_8_0_17', records_names, config_prop, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        assert '<property name="polarion-lookup-method" value="Name" />' in ElementTree.tostring(
            properties_element, 'utf-8').strip()

    def test_properties_lookup_config(self, config_prop, records_names):
        new_config = copy.deepcopy(config_prop)
        new_config['xunit_import_properties']['polarion-lookup-method'] = "ID"
        exporter = XunitExport(
            '5_8_0_17', records_names, new_config, transform_func=lambda: None)
        top_element = exporter._top_element()
        properties_element = exporter._properties_element(top_element)
        assert '<property name="polarion-lookup-method" value="ID" />' in ElementTree.tostring(
            properties_element, 'utf-8').strip()

    def test_properties_invalid_lookup(self, config_prop, records_ids):
        new_config = copy.deepcopy(config_prop)
        new_config['xunit_import_properties']['polarion-lookup-method'] = 'invalid'
        exporter = XunitExport('5_8_0_17', records_ids, new_config)
        with pytest.raises(Dump2PolarionException):
            exporter.export()


class TestE2E(object):
    def test_e2e_ids_notransform(self, config_prop, records_ids):
        exporter = XunitExport(
            '5_8_0_17', records_ids, config_prop, transform_func=lambda arg: arg)
        complete = exporter.export()
        fname = 'complete_notransform.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_transform(self, config_prop, records_ids):
        exporter = XunitExport('5_8_0_17', records_ids, config_prop)
        complete = exporter.export()
        fname = 'complete_transform.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_names_notransform(self, config_prop, records_names):
        exporter = XunitExport(
            '5_8_0_17', records_names, config_prop, transform_func=lambda arg: arg)
        complete = exporter.export()
        fname = 'complete_notransform_name.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_names_transform(self, config_prop, records_names):
        exporter = XunitExport('5_8_0_17', records_names, config_prop)
        complete = exporter.export()
        fname = 'complete_transform_name.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
