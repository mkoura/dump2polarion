# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Submit results to the Polarion® XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import os
import logging

import requests

# requests package backwards compatibility mess
# pylint: disable=import-error,ungrouped-imports
from requests.packages.urllib3.exceptions import InsecureRequestWarning as IRWrequests
requests.packages.urllib3.disable_warnings(IRWrequests)
try:
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning as IRWurllib3
    urllib3.disable_warnings(IRWurllib3)
except ImportError:
    pass


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def submit_to_polarion(xunit, config, **kwargs):
    """Submits results to Polarion®."""
    login = kwargs.get('user') or config.get('username') or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get('password') or config.get('password') or os.environ.get("POLARION_PASSWORD")

    if not all([login, pwd]):
        logger.error("Failed to submit results to Polarion - missing credentials")
        return

    if '<testcases' in xunit:
        submit_target = config.get('testcase_taget')
    elif '<testsuites' in xunit:
        submit_target = config.get('xunit_target')
    else:
        submit_target = None

    if not submit_target:
        logger.error("Failed to submit results to Polarion - missing submit target")
        return

    logger.info("Submitting results to {}".format(submit_target))
    files = {'file': ('results.xml', xunit)}
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
