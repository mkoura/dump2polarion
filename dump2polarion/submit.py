# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Submit results to the Polarion XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import os
import io
import logging

import requests

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.configuration import get_config
from dump2polarion.utils import xunit_fill_testrun_id

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


def _get_xml_input(xml_str, xml_file):
    xml_input = None
    if xml_str:
        xml_input = xml_str
    elif xml_file and os.path.exists(xml_file):
        with io.open(xml_file, encoding='utf-8') as input_file:
            xml_input = input_file.read()
    else:
        logger.error("Failed to submit results to Polarion - no data supplied")
    return xml_input


# pylint: disable=too-many-branches
def submit(xml_str=None, xml_file=None, config=None, **kwargs):
    """Submits results to the XUnit Importer."""
    xml_input = _get_xml_input(xml_str, xml_file)
    if not xml_input:
        return

    # get default configuration when missing
    config = config or get_config()
    login = kwargs.get('user') or config.get('username') or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get('password') or config.get('password') or os.environ.get("POLARION_PASSWORD")

    if not all([login, pwd]):
        logger.error("Failed to submit results to Polarion - missing credentials")
        return

    if '<testcases' in xml_input:
        submit_target = config.get('testcase_taget')
    elif '<testsuites' in xml_input:
        submit_target = config.get('xunit_target')
        if 'polarion-testrun-id' not in xml_input:
            if config.get('args'):
                testrun_id = config['args'].get('testrun_id')
            testrun_id = kwargs.get('testrun_id') or testrun_id
            if not testrun_id:
                logger.error("Failed to submit results to Polarion - missing testrun id")
                return
            try:
                xml_input = xunit_fill_testrun_id(xml_input, testrun_id)
            except Dump2PolarionException as err:
                logger.error(err)
                return
    else:
        submit_target = None

    if not submit_target:
        logger.error("Failed to submit results to Polarion - missing submit target")
        return

    logger.info("Submitting results to {}".format(submit_target))
    files = {'file': ('results.xml', xml_input)}
    try:
        response = requests.post(submit_target, files=files, auth=(login, pwd), verify=False)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    if response is None:
        logger.error("Failed to submit results to {}".format(submit_target))
    elif response:
        logger.info("Results received by XUnit Importer (HTTP status {})".format(
            response.status_code))
    else:
        logger.error("HTTP status {}: failed to submit results to {}".format(
            response.status_code, submit_target))

    return response


def submit_and_verify(xml_str=None, xml_file=None, config=None, **kwargs):
    """Submits results to the XUnit Importer and checks that it was imported."""
    xml_input = _get_xml_input(xml_str, xml_file)
    if not xml_input:
        return

    # get default configuration when missing
    config = config or get_config()

    if kwargs.get('no_verify'):
        verification_func = None
    else:
        msgbus_login = kwargs.get('msgbus_user') or config.get('msgbus_username') or kwargs.get(
            'user') or config.get('username') or os.environ.get("POLARION_USERNAME")
        msgbus_pwd = kwargs.get('msgbus_password') or config.get('msgbus_password') or kwargs.get(
            'password') or config.get('password') or os.environ.get("POLARION_PASSWORD")
        # avoid slow initialization of stomp when it's not needed
        from dump2polarion import msgbus
        verification_func = msgbus.get_verification_func(
            config.get('message_bus'),
            xml_input,
            user=msgbus_login,
            password=msgbus_pwd,
            log_file=kwargs.get('msgbus_log'))

    response = submit(xml_input, config=config, **kwargs)

    if verification_func:
        response = verification_func(skip=not response, timeout=kwargs.get('verify_timeout'))

    return bool(response)
