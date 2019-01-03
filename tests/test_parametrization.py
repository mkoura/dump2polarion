# encoding: utf-8
# pylint: disable=missing-docstring,no-self-use,redefined-outer-name

from __future__ import unicode_literals

import copy
import io
import os

import pytest

from dump2polarion.exporters.xunit_exporter import XunitExport
from dump2polarion.results.importer import import_results
from tests import conf


@pytest.fixture(scope="module")
def records_names():
    input_file = os.path.join(conf.DATA_PATH, "ostriz.json")
    return import_results(input_file)


@pytest.fixture(scope="module")
def config_cloudtp(config_prop):
    cloudtp = copy.deepcopy(config_prop)
    cloudtp["polarion-project-id"] = "CLOUDTP"
    cloudtp["cfme_parametrize"] = True
    return cloudtp


class TestParamE2E(object):
    def test_e2e_names_transform(self, config_cloudtp, records_names):
        exporter = XunitExport("5_8_0_17", records_names, config_cloudtp)
        complete = exporter.export()
        fname = "complete_parametrization.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
