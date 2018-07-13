# -*- coding: utf-8 -*-
"""
Configuration loading.
"""

from __future__ import absolute_import, unicode_literals

import io
import logging
import os

import six
import yaml

from dump2polarion.exceptions import Dump2PolarionException

DEFAULT_USER_CONF = "~/.config/dump2polarion.yaml"
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
    xunit_project = config.get("xunit_import_properties", {}).get("polarion-project-id")
    if xunit_project:
        config["polarion-project-id"] = xunit_project
        logger.warning(
            'Loading the "polarion-project-id" from legacy configuration "xunit_import_properties"'
            " instead of from top level"
        )
    else:
        raise Dump2PolarionException('The "polarion-project-id" key is missing in the config file')


def get_config(config_file=None):
    """Loads config file and returns its content."""
    default_conf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dump2polarion.yaml")
    user_conf = os.path.expanduser(config_file or DEFAULT_USER_CONF)

    try:
        with open(user_conf):
            pass
    except EnvironmentError:
        user_conf = None
        if config_file:
            raise Dump2PolarionException("Cannot open config file {}".format(config_file))

    with io.open(default_conf, encoding="utf-8") as input_file:
        config_settings = yaml.load(input_file)
    logger.debug("Default config loaded from %s", default_conf)

    if user_conf:
        with io.open(user_conf, encoding="utf-8") as input_file:
            config_settings_user = yaml.load(input_file)
        logger.info("Config loaded from %s", user_conf)

        # merge default and user configuration
        try:
            config_settings.update(config_settings_user)
        except ValueError as err:
            raise Dump2PolarionException(
                "Failed to load the '{}' config file: {}".format(user_conf, err)
            )

    _populate_urls(config_settings)
    _set_project_id(config_settings)
    _check_config(config_settings)

    return config_settings
