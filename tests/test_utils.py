# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import os
import io

import pytest

from tests import conf

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion import utils


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
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        filled = utils.xunit_fill_testrun_id(parsed, '5_8_0_17')
        assert filled == parsed

    def test_fill_testrun_invalid_xml(self):
        parsed = 'invalid'
        with pytest.raises(Dump2PolarionException):
            utils.xunit_fill_testrun_id(parsed, '5_8_0_17')

    def test_fill_testrun_no_properties(self):
        parsed = '<invalid />'
        with pytest.raises(Dump2PolarionException):
            utils.xunit_fill_testrun_id(parsed, '5_8_0_17')

    def test_fill_testrun_missing(self):
        fname = 'properties.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        filled = utils.xunit_fill_testrun_id(parsed, '5_8_0_17')
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled
