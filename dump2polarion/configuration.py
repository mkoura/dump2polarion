# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Configuration loading.
"""

from __future__ import unicode_literals, absolute_import

import os
import io
import logging
import yaml

from dump2polarion.exceptions import Dump2PolarionException


DEFAULT_USER_CONF = '~/.config/dump2polarion.yaml'

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def _check_config(config):
    missing = []
    for key in ('testcase_taget', 'xunit_target', 'message_bus'):
        if not config.get(key):
            missing.append(key)
    if missing:
        raise Dump2PolarionException(
            "Failed to find following keys in config file: {}\n"
            "Please see https://mojo.redhat.com/docs/DOC-1098563#config".format(', '.join(missing)))


def get_config(config_file=None):
    """Loads config file and returns its content."""
    default_conf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dump2polarion.yaml')
    user_conf = os.path.expanduser(config_file or DEFAULT_USER_CONF)

    try:
        with open(user_conf):
            pass
    except EnvironmentError:
        user_conf = None
        if config_file:
            raise Dump2PolarionException("Cannot open config file '{}'".format(config_file))

    with io.open(default_conf, encoding='utf-8') as input_file:
        config_settings = yaml.load(input_file)
    logger.debug("Default config loaded from '{}'".format(default_conf))

    if user_conf:
        with io.open(user_conf, encoding='utf-8') as input_file:
            config_settings_user = yaml.load(input_file)
        logger.info("Config loaded from '{}'".format(user_conf))

        # merge default and user configuration
        try:
            config_settings.update(config_settings_user)
        except ValueError as err:
            raise Dump2PolarionException(
                "Failed to load the '{}' config file: {}".format(user_conf, err))

    _check_config(config_settings)

    return config_settings
