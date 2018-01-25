# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Submit results to the Polarion XUnit/TestCase Importer.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os

import requests

from dump2polarion import configuration, utils, verify
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


def _get_queue_url(xml_root, config):
    if xml_root.tag == 'testcases':
        target = config.get('testcase_queue')
    elif xml_root.tag == 'testsuites':
        target = config.get('xunit_queue')
    else:
        return
    return target


def _get_credentials(config, **kwargs):
    login = kwargs.get('user') or config.get('username') or os.environ.get('POLARION_USERNAME')
    pwd = kwargs.get('password') or config.get('password') or os.environ.get('POLARION_PASSWORD')

    if not all([login, pwd]):
        raise Dump2PolarionException("Failed to submit results to Polarion - missing credentials")

    return (login, pwd)


def get_job_id(response):
    """Returns job ID of the import."""
    try:
        parsed = response.json()
        return parsed['files']['results.xml']['job-id']
    # pylint: disable=broad-except
    except Exception:
        return


def submit(xml_str=None, xml_file=None, xml_root=None, config=None, **kwargs):
    """Submits results to the Polarion Importer."""
    try:
        config = config or configuration.get_config()
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
        logger.info("Job ID: {}".format(get_job_id(response)))
    else:
        logger.error("HTTP status {}: failed to submit results to {}".format(
            response.status_code, submit_target))

    return response


def submit_and_verify(xml_str=None, xml_file=None, xml_root=None, config=None, **kwargs):
    """Submits results to the Polarion Importer and checks that it was imported."""
    try:
        config = config or configuration.get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        credentials = _get_credentials(config, **kwargs)
        queue_url = _get_queue_url(xml_root, config)
    except Dump2PolarionException as err:
        logger.error(err)
        return

    verify_import = True
    job_id = None
    if not kwargs.get('no_verify'):
        verification_queue = verify.QueueSearch(
            user=credentials[0], password=credentials[1], queue_url=queue_url)
        verify_import = verification_queue.queue_init()

    response = submit(xml_root=xml_root, config=config, **kwargs)

    if not verify_import:
        # we wanted to verify the import but it didn't happen for some reason
        return False

    if response:
        job_id = get_job_id(response)
    if not kwargs.get('no_verify') and job_id:
        response = verification_queue.verify_submit(
            job_id, timeout=kwargs.get('verify_timeout'), log_file=kwargs.get('log_file'))

    return bool(response)
