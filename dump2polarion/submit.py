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
    xunit_target = config.get('xunit_target')

    if not all([login, pwd]):
        logger.error("Failed to submit results to Polarion - missing credentials")
        return
    if not xunit_target:
        logger.error("Failed to submit results to Polarion - missing 'xunit_target'")
        return

    if os.path.isfile(xunit):
        files = {'file': ('results.xml', open(xunit, 'rb'))}
    else:
        files = {'file': ('results.xml', xunit)}

    logger.info("Submitting results to {}".format(xunit_target))
    try:
        response = requests.post(xunit_target, files=files, auth=(login, pwd), verify=False)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    if response is None:
        logger.error("Failed to submit results to {}".format(xunit_target))
    elif response:
        logger.info("Results received by XUnit Importer (HTTP status {})".format(
            response.status_code))
    else:
        logger.error("HTTP status {}: failed to submit results to {}".format(
            response.status_code, xunit_target))

    return response
