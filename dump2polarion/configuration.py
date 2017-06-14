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

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_config(config_file=None, args=None):
    """Loads config file and returns its content."""
    default_conf = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dump2polarion.yaml')
    user_conf = config_file or '~/.config/dump2polarion.yaml'

    try:
        with open(os.path.expanduser(user_conf)):
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

    if args:
        config_settings['args'] = args

    return config_settings
