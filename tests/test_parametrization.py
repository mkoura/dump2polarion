# encoding: utf-8
# pylint: disable=missing-docstring,no-self-use,too-few-public-methods,redefined-outer-name

from __future__ import unicode_literals

import io
import os

import pytest

from dump2polarion.importer import do_import
from dump2polarion.xunit_exporter import XunitExport
from tests import conf


@pytest.fixture(scope="module")
def records_names():
    input_file = os.path.join(conf.DATA_PATH, "ostriz.json")
    return do_import(input_file)


@pytest.fixture(scope="module")
def config_cloudtp(config_prop):
    config_prop["polarion-project-id"] = "CLOUDTP"
    config_prop["cfme_parametrize"] = True
    return config_prop


class TestParamE2E(object):
    def test_e2e_names_transform(self, config_cloudtp, records_names):
        exporter = XunitExport("5_8_0_17", records_names, config_cloudtp)
        complete = exporter.export()
        fname = "complete_parametrization.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
