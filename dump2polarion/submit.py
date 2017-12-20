# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Submit results to the Polarion XUnit/TestCase Importer.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os

import requests

from dump2polarion import msgbus, utils
from dump2polarion.configuration import get_config
from dump2polarion.exceptions import Dump2PolarionException

# requests package backwards compatibility mess
# pylint: disable=import-error,ungrouped-imports
from requests.packages.urllib3.exceptions import InsecureRequestWarning as IRWrequests
# pylint: disable=no-member
requests.packages.urllib3.disable_warnings(IRWrequests)
try:
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning as IRWurllib3
    urllib3.disable_warnings(IRWurllib3)
except ImportError:
    pass


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def _get_xml_root(xml_root, xml_str, xml_file):
    if xml_root is not None:
        return xml_root
    if xml_str:
        return utils.get_xml_root_from_str(xml_str)
    if xml_file:
        return utils.get_xml_root(xml_file)
    raise Dump2PolarionException("Failed to submit results to Polarion - no data supplied")


def _get_submit_target(xml_root, config):
    if xml_root.tag == 'testcases':
        target = config.get('testcase_taget')
    elif xml_root.tag == 'testsuites':
        target = config.get('xunit_target')
    else:
        raise Dump2PolarionException(
            "Failed to submit results to Polarion - submit target not found")
    return target


def _get_credentials(config, **kwargs):
    login = kwargs.get('user') or config.get('username') or os.environ.get('POLARION_USERNAME')
    pwd = kwargs.get('password') or config.get('password') or os.environ.get('POLARION_PASSWORD')

    if not all([login, pwd]):
        raise Dump2PolarionException("Failed to submit results to Polarion - missing credentials")

    return (login, pwd)


def submit(xml_str=None, xml_file=None, xml_root=None, config=None, **kwargs):
    """Submits results to the Polarion Importer."""
    try:
        config = config or get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        credentials = _get_credentials(config, **kwargs)
        submit_target = _get_submit_target(xml_root, config)
        utils.xunit_fill_testrun_id(xml_root, kwargs.get('testrun_id'))
        xml_input = utils.etree_to_string(xml_root)
    except Dump2PolarionException as err:
        logger.error(err)
        return

    logger.info("Submitting results to {}".format(submit_target))
    files = {'file': ('results.xml', xml_input)}
    try:
        response = requests.post(submit_target, files=files, auth=credentials, verify=False)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    if response is None:
        logger.error("Failed to submit results to {}".format(submit_target))
    elif response:
        logger.info("Results received by the Importer (HTTP status {})".format(
            response.status_code))
    else:
        logger.error("HTTP status {}: failed to submit results to {}".format(
            response.status_code, submit_target))

    return response


def submit_and_verify(xml_str=None, xml_file=None, xml_root=None, config=None, **kwargs):
    """Submits results to the Polarion Importer and checks that it was imported."""
    try:
        config = config or get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        response_property = utils.fill_response_property(xml_root)
    except Dump2PolarionException as err:
        logger.error(err)
        return False

    verification_skipped = False

    if kwargs.get('no_verify'):
        verification_func = None
    else:
        msgbus_login = kwargs.get('msgbus_user') or config.get('msgbus_username') or kwargs.get(
            'user') or config.get('username') or os.environ.get('POLARION_USERNAME')
        msgbus_pwd = kwargs.get('msgbus_password') or config.get('msgbus_password') or kwargs.get(
            'password') or config.get('password') or os.environ.get('POLARION_PASSWORD')

        verification_func = msgbus.get_verification_func(
            config.get('message_bus'),
            response_property,
            user=msgbus_login,
            password=msgbus_pwd,
            log_file=kwargs.get('msgbus_log'))
        if not verification_func:
            verification_skipped = True

    response = submit(xml_root=xml_root, config=config, **kwargs)

    if verification_func:
        response = verification_func(skip=not response, timeout=kwargs.get('verify_timeout'))
    elif verification_skipped:
        # we wanted to verify the import but it didn't happen for some reason
        response = False

    return bool(response)
