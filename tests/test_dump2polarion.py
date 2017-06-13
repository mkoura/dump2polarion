# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name

from __future__ import unicode_literals

import os
import copy

from xml.etree import ElementTree

import pytest

import dump2polarion as d2p
from dump2polarion.csvtools import import_csv
from dump2polarion.exceptions import Dump2PolarionException


DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


@pytest.fixture(scope="module")
def config():
    return {
        'xunit_import_properties': {
            'polarion-dry-run': False,
            'polarion-project-id': 'RHCF3',
            'polarion-testrun-status-id': 'inprogress',
            'polarion-response-test': 'test'
        }
    }


@pytest.fixture(scope="module")
def records_ids():
    csv_file = os.path.join(DATA_PATH, 'workitems_ids.csv')
    return import_csv(csv_file)


@pytest.fixture(scope="module")
def records_names():
    csv_file = os.path.join(DATA_PATH, 'workitems_ids.csv')
    records = import_csv(csv_file)
    for res in records.results:
        res.pop('id')
    return records


def test_top_element(config, records_ids):
    exporter = d2p.XunitExport('5_8_0_17', records_ids, config, transform_func=lambda: None)
    top_element = exporter.top_element()
    parsed = '<testsuites><!--Generated for testrun 5_8_0_17--></testsuites>'.strip()
    assert ElementTree.tostring(top_element, 'utf-8').strip() == parsed


def test_properties_element(config, records_ids):
    exporter = d2p.XunitExport('5_8_0_17', records_ids, config, transform_func=lambda: None)
    top_element = exporter.top_element()
    properties_element = exporter.properties_element(top_element)
    parsed = """
<properties><property name="polarion-testrun-id" value="5_8_0_17" /><property name="polarion-dry-run" value="False" /><property name="polarion-testrun-status-id" value="inprogress" /><property name="polarion-response-test" value="test" /><property name="polarion-project-id" value="RHCF3" /><property name="polarion-lookup-method" value="ID" /></properties>
""".strip()
    assert ElementTree.tostring(properties_element, 'utf-8').strip() == parsed


def test_e2e_ids_notransform(config, records_ids):
    exporter = d2p.XunitExport('5_8_0_17', records_ids, config, transform_func=lambda arg: arg)
    complete = exporter.export()
    fname = 'complete_notransform.xml'
    with open(os.path.join(DATA_PATH, fname)) as input_xml:
        parsed = input_xml.read()
    assert complete == parsed


def test_e2e_ids_transform(config, records_ids):
    exporter = d2p.XunitExport('5_8_0_17', records_ids, config)
    complete = exporter.export()
    fname = 'complete_transform.xml'
    with open(os.path.join(DATA_PATH, fname)) as input_xml:
        parsed = input_xml.read()
    assert complete == parsed


def test_e2e_names_notransform(config, records_names):
    exporter = d2p.XunitExport('5_8_0_17', records_names, config, transform_func=lambda arg: arg)
    complete = exporter.export()
    fname = 'complete_notransform_name.xml'
    with open(os.path.join(DATA_PATH, fname)) as input_xml:
        parsed = input_xml.read()
    assert complete == parsed


def test_e2e_names_transform(config, records_names):
    exporter = d2p.XunitExport('5_8_0_17', records_names, config)
    complete = exporter.export()
    fname = 'complete_transform_name.xml'
    with open(os.path.join(DATA_PATH, fname)) as input_xml:
        parsed = input_xml.read()
    assert complete == parsed


def test_invalid_lookup_method(config, records_ids):
    new_config = copy.deepcopy(config)
    new_config['xunit_import_properties']['polarion-lookup-method'] = 'invalid'
    exporter = d2p.XunitExport('5_8_0_17', records_ids, new_config)
    with pytest.raises(Dump2PolarionException):
        exporter.export()
