# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os
import io

import pytest
from tests import conf

from dump2polarion import ostriztools
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.exporter import XunitExport


@pytest.fixture(scope="module")
def records_json():
    json_file = os.path.join(conf.DATA_PATH, 'ostriz.json')
    return ostriztools.import_ostriz(json_file)


class TestOstriz(object):
    def test_testrun_id_simple(self):
        testrun_id = ostriztools._get_testrun_id('5.8.0.17')
        assert testrun_id == '5_8_0_17'

    def test_testrun_id_build(self):
        testrun_id = ostriztools._get_testrun_id('5.8.0.17-20170525183055_6317a22')
        assert testrun_id == '5_8_0_17'

    def test_testrun_id_fill(self):
        testrun_id = ostriztools._get_testrun_id('5.8.0.7-2017')
        assert testrun_id == '5_8_0_07'

    def test_testrun_id_invalid(self):
        with pytest.raises(Dump2PolarionException):
            ostriztools._get_testrun_id('INVALID')

    def test_duration_good(self):
        duration = ostriztools._calculate_duration(1495766591.151192, 1495768544.573208)
        assert duration == 1953

    def test_duration_bad_finish(self):
        duration = ostriztools._calculate_duration(1495766591.151192, None)
        assert duration == 0

    def test_duration_bad_start(self):
        duration = ostriztools._calculate_duration(0, 1495768544.573208)
        assert duration == 0

    def test_import_orig_data(self, records_json):
        assert hasattr(records_json, 'results')
        assert len(records_json.results) == 6
        assert 'title' in records_json.results[0]
        assert hasattr(records_json, 'testrun')
        assert records_json.testrun == '5_8_0_17'

    def test_invalid_json(self):
        fname = 'junit-report.xml'
        with pytest.raises(Dump2PolarionException):
            ostriztools._get_json(os.path.join(conf.DATA_PATH, fname))

    def test_no_json(self):
        with pytest.raises(Dump2PolarionException):
            ostriztools.import_ostriz('NONEXISTENT.json')

    def test_e2e_ids_notransform(self, config_prop, records_json):
        exporter = XunitExport(
            '5_8_0_17', records_json, config_prop, transform_func=lambda arg: arg)
        complete = exporter.export()
        fname = 'ostriz_notransform.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_transform(self, config_prop, records_json):
        exporter = XunitExport('5_8_0_17', records_json, config_prop)
        complete = exporter.export()
        fname = 'ostriz_transform.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
