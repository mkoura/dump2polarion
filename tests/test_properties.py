# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,invalid-name

from __future__ import unicode_literals

import os

import pytest

from dump2polarion import properties, utils
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf


# pylint: disable=too-many-public-methods
class TestProperties(object):
    def test_fill_testrun_present(self):
        fname = "complete_notransform.xml"
        fname = os.path.join(conf.DATA_PATH, fname)
        xml_root = utils.get_xml_root(fname)
        properties.xunit_fill_testrun_id(xml_root, "not_used")
        filled = utils.etree_to_string(xml_root)
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled

    def test_fill_testrun_invalid_xml(self):
        xml_root = utils.get_xml_root_from_str("<invalid/>")
        with pytest.raises(Dump2PolarionException) as excinfo:
            properties.xunit_fill_testrun_id(xml_root, "5_8_0_17")
        assert "missing <testsuites>" in str(excinfo.value)

    def test_fill_testrun_no_properties(self):
        xml_root = utils.get_xml_root_from_str("<testsuites/>")
        with pytest.raises(Dump2PolarionException) as excinfo:
            properties.xunit_fill_testrun_id(xml_root, "5_8_0_17")
        assert "Failed to find <properties> in the XML file" in str(excinfo.value)

    def test_fill_testrun_missing(self):
        fname = "properties.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        properties.xunit_fill_testrun_id(xml_root, "5_8_0_17")
        filled = utils.etree_to_string(xml_root)
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled

    @pytest.mark.parametrize("fname", ("testcases.xml", "complete_transform.xml"))
    def test_nofill_response(self, fname):
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = properties.fill_response_property(xml_root)
        assert name == "test"
        assert value == "test"

    @pytest.mark.parametrize("fname", ("testcases_noresponse.xml", "testcases_noresponse2.xml"))
    def test_fill_testcase_response(self, fname):
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = properties.fill_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert name == "dump2polarion"
        assert value
        assert '<response-property name="dump2polarion" value=' in filled

    def test_fill_testsuites_response(self):
        fname = "complete_transform_noresponse.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = properties.fill_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert name == "dump2polarion"
        assert value
        assert '<property name="polarion-response-dump2polarion" value=' in filled

    def test_fill_custom_testcase_response(self):
        fname = "testcases_noresponse.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = properties.fill_response_property(xml_root, "test", "test")
        filled = utils.etree_to_string(xml_root)
        assert name == "test"
        assert value == "test"
        assert '<response-property name="test" value="test"' in filled
        # make sure response properties are on top
        assert '<testcases project-id="RHCF3">\n  <response-properties>' in filled

    def test_fill_custom_testsuites_response(self):
        fname = "complete_transform_noresponse.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = properties.fill_response_property(xml_root, "test", "test")
        filled = utils.etree_to_string(xml_root)
        assert name == "test"
        assert value == "test"
        assert '<property name="polarion-response-test" value="test"' in filled

    def test_fill_invalid_testsuites_response(self):
        xml_root = utils.get_xml_root_from_str("<invalid/>")
        with pytest.raises(Dump2PolarionException) as excinfo:
            properties.fill_response_property(xml_root, "test", "test")
        assert "XML file is not in expected format" in str(excinfo.value)

    def test_remove_testsuites_response_property(self):
        fname = "complete_transform.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert '<property name="polarion-response-test"' in filled
        properties.remove_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert '<property name="polarion-response-test"' not in filled

    def test_remove_testcases_response_property(self):
        fname = "testcases.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert '<response-property name="test"' in filled
        properties.remove_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert "<response-properties" not in filled

    def test_add_testsuites_lookup_property(self):
        fname = "complete_noprop.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert "polarion-lookup-method" not in filled
        properties.set_lookup_method(xml_root, "name")
        filled = utils.etree_to_string(xml_root)
        assert 'property name="polarion-lookup-method" value="name"' in filled

    def test_add_testcases_lookup_property(self):
        fname = "testcases_noprop.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert "lookup-method" not in filled
        properties.set_lookup_method(xml_root, "name")
        filled = utils.etree_to_string(xml_root)
        assert 'property name="lookup-method" value="name"' in filled

    def test_add_testsuites_dry_run(self):
        fname = "complete_noprop.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert "polarion-dry-run" not in filled
        properties.set_dry_run(xml_root, True)
        filled = utils.etree_to_string(xml_root)
        assert 'property name="polarion-dry-run" value="true"' in filled

    def test_add_testcases_dry_run(self):
        fname = "testcases_noprop.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        filled = utils.etree_to_string(xml_root)
        assert "dry-run" not in filled
        properties.set_dry_run(xml_root, True)
        filled = utils.etree_to_string(xml_root)
        assert 'property name="dry-run" value="true"' in filled
