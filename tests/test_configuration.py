# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os
import pytest

from tests import conf

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion import configuration


class TestConfiguration(object):
    def test_nonexistant(self):
        with pytest.raises(Dump2PolarionException):
            configuration.get_config('nonexistant')

    def test_default(self):
        with pytest.raises(Dump2PolarionException):
            configuration.get_config()

    def test_user(self):
        conf_file = os.path.join(conf.DATA_PATH, 'dump2polarion.yaml')
        cfg = configuration.get_config(conf_file)
        assert cfg['xunit_import_properties']['polarion-dry-run'] is True
        assert cfg['username'] == 'user1'
        assert cfg['xunit_import_properties']['polarion-project-id'] == 'RHCF3'

    def test_check_config(self):
        cfg = {}
        with pytest.raises(Dump2PolarionException):
            configuration._check_config(cfg)
