# -*- coding: utf-8 -*-
"""
Submit data to the Polarion Importer.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os

from dump2polarion import configuration, properties, utils
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.verify import verify_submit

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def _get_xml_root(xml_root, xml_str, xml_file):
    if xml_root is not None:
        return xml_root
    if xml_str:
        return utils.get_xml_root_from_str(xml_str)
    if xml_file:
        return utils.get_xml_root(xml_file)
    raise Dump2PolarionException("Failed to submit to Polarion - no data supplied")


def _get_submit_target(xml_root, config):
    if xml_root.tag == "testcases":
        target = config.get("testcase_taget")
    elif xml_root.tag == "testsuites":
        target = config.get("xunit_target")
    elif xml_root.tag == "requirements":
        target = config.get("requirement_target")
    else:
        raise Dump2PolarionException("Failed to submit to Polarion - submit target not found")
    return target


def _get_queue_url(xml_root, config):
    if xml_root.tag == "testcases":
        target = config.get("testcase_queue")
    elif xml_root.tag == "testsuites":
        target = config.get("xunit_queue")
    elif xml_root.tag == "requirements":
        target = config.get("requirement_queue")
    else:
        return None
    return target


def _get_log_url(xml_root, config):
    if xml_root.tag == "testcases":
        target = config.get("testcase_log")
    elif xml_root.tag == "testsuites":
        target = config.get("xunit_log")
    elif xml_root.tag == "requirements":
        target = config.get("requirement_log")
    else:
        return None
    return target


def response2dict(response):
    """Returns dict of the response."""
    try:
        return response.json()
    # pylint: disable=broad-except
    except Exception:
        return None


def get_job_ids(response):
    """Returns job IDs of the import."""
    if not isinstance(response, dict):
        response = response2dict(response)
    if response:
        return response["files"]["results.xml"]["job-ids"]
    return None


def get_error_message(response):
    """Returns job IDs of the import."""
    if not isinstance(response, dict):
        response = response2dict(response)
    if response:
        return response["files"]["results.xml"].get("error-message")
    return None


def validate_response(response, submit_target):
    """Checks that the response is valid and import succeeded."""
    if response is None:
        logger.error("Failed to submit to %s", submit_target)
        return False

    if not response:
        logger.error("HTTP status %d: failed to submit to %s", response.status_code, submit_target)
        return False

    parsed_response = response2dict(response)

    if not parsed_response:
        logger.error("Submit to %s failed, invalid response received", submit_target)
        return False

    error_message = get_error_message(parsed_response)
    if error_message:
        logger.error("Submit to %s failed with error", submit_target)
        logger.debug("Error message: %s", error_message)
        return False

    job_ids = get_job_ids(parsed_response)
    if not job_ids or job_ids == [0]:
        logger.error("Submit to %s failed to get job id", submit_target)
        return False

    logger.info("Results received by the Importer (HTTP status %d)", response.status_code)
    logger.info("Job IDs: %s", job_ids)

    return response


def _get_credentials(config, **kwargs):
    login = kwargs.get("user") or config.get("username") or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get("password") or config.get("password") or os.environ.get("POLARION_PASSWORD")

    if not all([login, pwd]):
        raise Dump2PolarionException("Failed to submit to Polarion - missing credentials")

    return (login, pwd)


# pylint: disable=too-many-arguments
def submit(
    xml_str=None, xml_file=None, xml_root=None, config=None, session=None, dry_run=None, **kwargs
):
    """Submits data to the Polarion Importer."""
    try:
        config = config or configuration.get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        credentials = _get_credentials(config, **kwargs)
        submit_target = _get_submit_target(xml_root, config)
        properties.xunit_fill_testrun_id(xml_root, kwargs.get("testrun_id"))
        if dry_run is not None:
            properties.set_dry_run(xml_root, dry_run)
        xml_input = utils.etree_to_string(xml_root)
        session = session or utils.get_session(credentials, config)
    except Dump2PolarionException as err:
        logger.error(err)
        return None

    logger.info("Submitting data to %s", submit_target)
    files = {"file": ("results.xml", xml_input)}
    try:
        response = session.post(submit_target, files=files)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    return validate_response(response, submit_target)


# pylint: disable=too-many-arguments
def submit_and_verify(
    xml_str=None, xml_file=None, xml_root=None, config=None, session=None, dry_run=None, **kwargs
):
    """Submits data to the Polarion Importer and checks that it was imported."""
    try:
        config = config or configuration.get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        credentials = _get_credentials(config, **kwargs)
        queue_url = _get_queue_url(xml_root, config)
        log_url = _get_log_url(xml_root, config)
        session = session or utils.get_session(credentials, config)
    except Dump2PolarionException as err:
        logger.error(err)
        return None

    response = submit(xml_root=xml_root, config=config, session=session, dry_run=dry_run, **kwargs)
    if not response:
        return False

    job_ids = get_job_ids(response)
    if not kwargs.get("no_verify") and job_ids:
        response = verify_submit(
            session,
            queue_url,
            log_url,
            job_ids,
            timeout=kwargs.get("verify_timeout"),
            log_file=kwargs.get("log_file"),
        )

    return bool(response)
