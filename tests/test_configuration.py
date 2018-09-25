# encoding: utf-8
# pylint: disable=missing-docstring,no-self-use,protected-access

from __future__ import unicode_literals

import os

import pytest

from dump2polarion import configuration
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf


class TestConfiguration(object):
    def test_nonexistant(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            configuration.get_config("nonexistant")
        assert "Cannot open config file nonexistant" in str(excinfo.value)

    def test_default(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            configuration.get_config()
        assert "Failed to find following keys in config file" in str(excinfo.value)

    def test_user(self, config_e2e):
        cfg = configuration.get_config(config_e2e)
        assert cfg["xunit_import_properties"]["polarion-dry-run"] is False
        assert cfg["username"] == "user1"
        assert cfg["polarion-project-id"] == "RHCF3"

    @pytest.mark.parametrize("config", ["polarion_tools_legacy.yaml", "polarion_tools.yaml"])
    def test_populate(self, config):
        conf_file = os.path.join(conf.DATA_PATH, config)
        cfg = configuration.get_config(conf_file)
        polarion_url = cfg.get("polarion_url")
        for key in configuration.URLS:
            assert key in cfg
            if polarion_url and cfg.get(key):
                assert polarion_url in cfg[key]

    def test_check_config(self):
        cfg = {}
        with pytest.raises(Dump2PolarionException) as excinfo:
            configuration._check_config(cfg)
        assert "Failed to find following keys in config file" in str(excinfo.value)
