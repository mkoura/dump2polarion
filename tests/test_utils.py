# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use

from __future__ import unicode_literals

import os

import pytest
from mock import patch

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf


# pylint: disable=too-many-public-methods
class TestUtils(object):
    def test_get_unicode_char(self):
        unicode_str = utils.get_unicode_str("®")
        assert unicode_str == "®"

    def test_get_unicode_num(self):
        unicode_str = utils.get_unicode_str(42)
        assert unicode_str == "42"

    def test_get_unicode_basestring(self):
        unicode_str = utils.get_unicode_str("@".encode("ascii"))
        assert unicode_str == "@"

    def test_write_xml_gen(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml("<xml />", output_loc=dirname)
        assert "output-" in os.listdir(dirname)[0]

    def test_write_xml_loc(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml("<xml />", output_loc=os.path.join(dirname, "output123.xml"))
        assert "output123.xml" in os.listdir(dirname)[0]

    def test_write_xml_file(self, tmpdir):
        dirname = str(tmpdir)
        utils.write_xml("<xml />", filename=os.path.join(dirname, "output123.xml"))
        assert "output123.xml" in os.listdir(dirname)[0]

    def test_write_xml_root_none(self, tmpdir):
        dirname = str(tmpdir)
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.write_xml_root(None, filename=os.path.join(dirname, "output123.xml"))
        assert "No data to write" in str(excinfo.value)

    def test_write_xml_root_file(self, tmpdir):
        fname = "complete_transform_noresponse.xml"
        xml_root = utils.get_xml_root(os.path.join(conf.DATA_PATH, fname))
        dirname = str(tmpdir)
        utils.write_xml_root(xml_root, filename=os.path.join(dirname, "output123.xml"))
        assert "output123.xml" in os.listdir(dirname)[0]

    def test_write_xml_no_data(self, tmpdir):
        dirname = str(tmpdir)
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.write_xml("", filename=os.path.join(dirname, "output123.xml"))
        assert "No data to write" in str(excinfo.value)

    def test_invalid_xml_root(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.get_xml_root("NONEXISTENT.xml")
        assert "Failed to parse XML file" in str(excinfo.value)

    def test_invalid_xml_str(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            utils.get_xml_root_from_str(None)
        assert "Failed to parse XML string" in str(excinfo.value)

    def test_get_session_oldauth(self, config_prop):
        if "auth_url" in config_prop:
            del config_prop["auth_url"]
        with patch("requests.Session"):
            session = utils.get_session("foo", config_prop)
        assert session.auth == "foo"

    def test_get_session_cookie_failed(self, config_prop):
        config_prop["auth_url"] = "http://example.com"
        with patch("requests.Session") as mock:
            instance = mock.return_value
            instance.post.return_value = None
            with pytest.raises(Dump2PolarionException) as excinfo:
                utils.get_session("foo", config_prop)
        assert "Cookie was not retrieved" in str(excinfo.value)

    def test_get_session_cookie_success(self, config_prop):
        config_prop["auth_url"] = "http://example.com"
        with patch("requests.Session") as mock:
            instance = mock.return_value
            instance.post.return_value = True
            session = utils.get_session("foo", config_prop)
        assert session.auth != "foo"
