# -*- coding: utf-8 -*-
"""
Configuration loading.
"""

from __future__ import absolute_import, unicode_literals

import glob
import io
import logging
import os

import six
import yaml

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.utils import find_vcs_root

DEFAULT_CONF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "polarion_tools.yaml")
PROJECT_CONF_DIRS = ("conf", ".")
PROJECT_CONF = "polarion_tools*.yaml"

URLS = {
    "testcase_taget": "import/testcase",
    "xunit_target": "import/xunit",
    "requirement_target": "import/requirement",
    "testcase_queue": "import/testcase-queue",
    "xunit_queue": "import/xunit-queue",
    "requirement_queue": "import/requirement-queue",
    "testcase_log": "import/testcase-log",
    "xunit_log": "import/xunit-log",
    "requirement_log": "import/requirement-log",
    "auth_url": "j_security_check",
}

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def _check_config(config):
    missing = []
    for key in six.iterkeys(URLS):
        if not config.get(key):
            missing.append(key)

    # the 'auth_url' is allowed to be empty for now
    # TODO: can be removed once basic auth is discontinued on prod
    if not config.get("auth_url") and "auth_url" in config:
        missing.remove("auth_url")

    if missing:
        raise Dump2PolarionException(
            "Failed to find following keys in config file: {}\n"
            "Please see https://mojo.redhat.com/docs/DOC-1098563#config".format(", ".join(missing))
        )


def _guess_base_url(config):
    for key, value in six.iteritems(URLS):
        if config.get(key):
            return config[key][: -len(value)]
    return None


def _populate_urls(config):
    base_url = config.get("polarion_url")
    if not base_url:
        base_url = _guess_base_url(config)
    if not base_url:
        return

    base_url = base_url.rstrip("/")
    for key, url in six.iteritems(URLS):
        if key not in config:
            config[key] = "{}/{}".format(base_url, url)


def _set_project_id(config):
    if config.get("polarion-project-id"):
        return

    # use legacy configuration if available
    xunit_project = config.get("xunit_import_properties") or {}
    xunit_project = xunit_project.get("polarion-project-id")
    if not xunit_project:
        raise Dump2PolarionException('The "polarion-project-id" key is missing in the config file')

    config["polarion-project-id"] = xunit_project
    logger.warning(
        'Loading the "polarion-project-id" from legacy configuration "xunit_import_properties"'
        " instead of from top level"
    )


def _get_default_conf():
    with io.open(DEFAULT_CONF, encoding="utf-8") as input_file:
        config_settings = yaml.load(input_file)

    logger.debug("Default config loaded from %s", DEFAULT_CONF)

    return config_settings


def _get_user_conf(config_file):
    try:
        with io.open(os.path.expanduser(config_file), encoding="utf-8") as input_file:
            config_settings = yaml.load(input_file)
    except EnvironmentError:
        raise Dump2PolarionException("Cannot open config file {}".format(config_file))

    logger.info("Config loaded from %s", config_file)

    return config_settings


def _get_project_conf():
    """Loads configuration from project config file."""
    config_settings = {}

    project_root = find_vcs_root(".")
    if project_root is None:
        return config_settings

    for conf_dir in PROJECT_CONF_DIRS:
        conf_dir = conf_dir.lstrip("./")
        joined_dir = os.path.join(project_root, conf_dir) if conf_dir else project_root
        joined_glob = os.path.join(joined_dir, PROJECT_CONF)
        conf_files = glob.glob(joined_glob)
        if conf_files:
            break
    else:
        conf_files = []

    for conf_file in conf_files:
        try:
            with io.open(conf_file, encoding="utf-8") as input_file:
                loaded_settings = yaml.load(input_file)
        except EnvironmentError:
            pass
        else:
            logger.info("Config loaded from %s", conf_file)
            config_settings.update(loaded_settings)

    return config_settings


def get_config(config_file=None, config_values=None):
    """Loads config file and returns its content."""
    config_values = config_values or {}
    config_settings = {}

    default_conf = _get_default_conf()
    user_conf = _get_user_conf(config_file) if config_file else {}
    # load project configuration only when user configuration was not specified
    project_conf = {} if user_conf else _get_project_conf()

    # merge configuration
    config_settings.update(default_conf)
    config_settings.update(user_conf)
    config_settings.update(project_conf)
    config_settings.update(config_values)

    _populate_urls(config_settings)
    _set_project_id(config_settings)
    _check_config(config_settings)

    return config_settings
