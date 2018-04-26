# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,invalid-name

from __future__ import unicode_literals

import os

import pytest

from mock import patch
from tests import conf

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException


# pylint: disable=too-many-public-methods
class TestUtils(object):
    def test_get_unicode_char(self):
        unicode_str = utils.get_unicode_str(u'®')
        assert unicode_str == u'®'

    def test_get_unicode_num(self):
        unicode_str = utils.get_unicode_str(42)
        assert unicode_str == u'42'

    def test_get_unicode_basestring(self):
        unicode_str = utils.get_unicode_str('@'.encode('ascii'))
        assert unicode_str == u'@'

    def test_fill_testrun_present(self):
        fname = 'complete_notransform.xml'
        fname = os.path.join(conf.DATA_PATH, fname)
        xml_root = utils.get_xml_root(fname)
        utils.xunit_fill_testrun_id(xml_root, 'not_used')
        filled = utils.etree_to_string(xml_root)
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled

    def test_fill_testrun_invalid_xml(self):
        xml_root = utils.get_xml_root_from_str('<invalid/>')
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.xunit_fill_testrun_id(xml_root, '5_8_0_17')
        assert 'missing <testsuites>' in str(excinfo.value)

    def test_fill_testrun_no_properties(self):
        xml_root = utils.get_xml_root_from_str('<testsuites/>')
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.xunit_fill_testrun_id(xml_root, '5_8_0_17')
        assert 'Failed to find <properties> in the XML file' in str(excinfo.value)

    def test_fill_testrun_missing(self):
        fname = 'properties.xml'
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        utils.xunit_fill_testrun_id(xml_root, '5_8_0_17')
        filled = utils.etree_to_string(xml_root)
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled

    @pytest.mark.parametrize(
        'fname',
        (
            'testcases.xml',
            'complete_transform.xml',
        ))
    def test_nofill_response(self, fname):
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = utils.fill_response_property(xml_root)
        assert name == 'test'
        assert value == 'test'

    @pytest.mark.parametrize(
        'fname',
        (
            'testcases_noresponse.xml',
            'testcases_noresponse2.xml',
        ))
    def test_fill_testcase_response(self, fname):
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = utils.fill_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert name == 'dump2polarion'
        assert value
        assert '<response-property name="dump2polarion" value=' in filled

    def test_fill_testsuites_response(self):
        fname = 'complete_transform_noresponse.xml'
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = utils.fill_response_property(xml_root)
        filled = utils.etree_to_string(xml_root)
        assert name == 'dump2polarion'
        assert value
        assert '<property name="polarion-response-dump2polarion" value=' in filled

    def test_fill_custom_testcase_response(self):
        fname = 'testcases_noresponse.xml'
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = utils.fill_response_property(xml_root, 'test', 'test')
        filled = utils.etree_to_string(xml_root)
        assert name == 'test'
        assert value == 'test'
        assert '<response-property name="test" value="test"' in filled
        # make sure response properties are on top
        assert '<testcases project-id="RHCF3">\n  <response-properties>' in filled

    def test_fill_custom_testsuites_response(self):
        fname = 'complete_transform_noresponse.xml'
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        name, value = utils.fill_response_property(xml_root, 'test', 'test')
        filled = utils.etree_to_string(xml_root)
        assert name == 'test'
        assert value == 'test'
        assert '<property name="polarion-response-test" value="test"' in filled

    def test_fill_invalid_testsuites_response(self):
        xml_root = utils.get_xml_root_from_str('<invalid/>')
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.fill_response_property(xml_root, 'test', 'test')
        assert 'XML file is not in expected format' in str(excinfo.value)

    def test_write_xml_gen(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml('<xml />', output_loc=dirname)
        assert 'output-' in os.listdir(dirname)[0]

    def test_write_xml_loc(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml('<xml />', output_loc=os.path.join(dirname, 'output123.xml'))
        assert 'output123.xml' in os.listdir(dirname)[0]

    def test_write_xml_file(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml('<xml />', filename=os.path.join(dirname, 'output123.xml'))
        assert 'output123.xml' in os.listdir(dirname)[0]

    def test_write_xml_no_data(self, tmpdir):
        dirname = str(tmpdir)
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.write_xml('', filename=os.path.join(dirname, 'output123.xml'))
        assert 'No data to write' in str(excinfo.value)

    def test_invalid_xml_root(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.get_xml_root('NONEXISTENT.xml')
        assert 'Failed to parse XML file' in str(excinfo.value)

    def test_invalid_xml_str(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.get_xml_root_from_str(None)
        assert 'Failed to parse XML file' in str(excinfo.value)

    def test_get_session_oldauth(self, config_prop):
        if 'auth_url' in config_prop:
            del config_prop['auth_url']
        with patch('requests.Session'):
            session = utils.get_session('foo', config_prop)
        assert session.auth == 'foo'

    def test_get_session_cookie_failed(self, config_prop):
        config_prop['auth_url'] = 'http://example.com'
        with patch('requests.Session') as mock:
            instance = mock.return_value
            instance.post.return_value = None
            with pytest.raises(Dump2PolarionException) as excinfo:
                utils.get_session('foo', config_prop)
        assert 'Cookie was not retrieved' in str(excinfo.value)

    def test_get_session_cookie_success(self, config_prop):
        config_prop['auth_url'] = 'http://example.com'
        with patch('requests.Session') as mock:
            instance = mock.return_value
            instance.post.return_value = True
            session = utils.get_session('foo', config_prop)
        assert session.auth != 'foo'
