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


class SubmitResponse(object):
    """Response data from submit to Importer."""

    def __init__(self, response):
        self.response = response
        self.parsed_response = self.response2dict()
        self.job_ids = self.get_job_ids()

    def response2dict(self):
        """Returns dict of the response."""
        try:
            return self.response.json()
        # pylint: disable=broad-except
        except Exception:
            return None

    def get_job_ids(self):
        """Returns job IDs of the import."""
        if not self.parsed_response:
            return None
        try:
            job_ids = self.parsed_response["files"]["results.xml"]["job-ids"]
        except KeyError:
            return None
        if not job_ids or job_ids == [0]:
            return None
        return job_ids

    def get_error_message(self):
        """Returns job IDs of the import."""
        if self.parsed_response:
            return self.parsed_response["files"]["results.xml"].get("error-message")
        return None

    def validate_response(self):
        """Checks that the response is valid and import succeeded."""
        if self.response is None:
            logger.error("Failed to submit")
            return False

        if not self.response:
            logger.error(
                "HTTP status %d: failed to submit to %s",
                self.response.status_code,
                self.response.url,
            )
            return False

        if not self.parsed_response:
            logger.error("Submit to %s failed, invalid response received", self.response.url)
            return False

        error_message = self.get_error_message()
        if error_message:
            logger.error("Submit to %s failed with error", self.response.url)
            logger.debug("Error message: %s", error_message)
            return False

        if not self.job_ids:
            logger.error("Submit to %s failed to get job id", self.response.url)
            return False

        logger.info("Results received by the Importer (HTTP status %d)", self.response.status_code)
        logger.info("Job IDs: %s", self.job_ids)

        return True

    def __len__(self):
        return 1 if self.job_ids else 0

    def __repr__(self):
        return repr(self.response)


class SubmitConfig(object):
    """Configuration for data submit."""

    def __init__(self, xml_root, config, **kwargs):
        self.xml_root = xml_root
        self.config = config
        self.submit_kwargs = kwargs

        self.submit_target = None
        self.queue_url = None
        self.log_url = None
        self.credentials = None

        self.get_targets()
        self.get_credentials(**self.submit_kwargs)

    def get_targets(self):
        """Sets targets."""
        if self.xml_root.tag == "testcases":
            self.submit_target = self.config.get("testcase_taget")
            self.queue_url = self.config.get("testcase_queue")
            self.log_url = self.config.get("testcase_log")
        elif self.xml_root.tag == "testsuites":
            self.submit_target = self.config.get("xunit_target")
            self.queue_url = self.config.get("xunit_queue")
            self.log_url = self.config.get("xunit_log")
        elif self.xml_root.tag == "requirements":
            self.submit_target = self.config.get("requirement_target")
            self.queue_url = self.config.get("requirement_queue")
            self.log_url = self.config.get("requirement_log")
        else:
            raise Dump2PolarionException("Failed to submit to Polarion - submit target not found")

    def get_credentials(self, **kwargs):
        """Sets credentails."""
        login = (
            kwargs.get("user") or os.environ.get("POLARION_USERNAME") or self.config.get("username")
        )
        pwd = (
            kwargs.get("password")
            or os.environ.get("POLARION_PASSWORD")
            or self.config.get("password")
        )

        if not all([login, pwd]):
            raise Dump2PolarionException("Failed to submit to Polarion - missing credentials")

        self.credentials = (login, pwd)


def _get_xml_root(xml_root, xml_str, xml_file):
    if xml_root is not None:
        return xml_root
    if xml_str:
        return utils.get_xml_root_from_str(xml_str)
    if xml_file:
        return utils.get_xml_root(xml_file)
    raise Dump2PolarionException("Failed to submit to Polarion - no data supplied")


def submit(xml_root, submit_config, session, dry_run=None, **kwargs):
    """Submits data to the Polarion Importer."""
    properties.xunit_fill_testrun_id(xml_root, kwargs.get("testrun_id"))
    if dry_run is not None:
        properties.set_dry_run(xml_root, dry_run)
    xml_input = utils.etree_to_string(xml_root)

    logger.info("Submitting data to %s", submit_config.submit_target)
    files = {"file": ("results.xml", xml_input)}
    try:
        response = session.post(submit_config.submit_target, files=files)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    return SubmitResponse(response)


# pylint: disable=too-many-arguments
def submit_and_verify(
    xml_str=None, xml_file=None, xml_root=None, config=None, session=None, dry_run=None, **kwargs
):
    """Submits data to the Polarion Importer and checks that it was imported."""
    try:
        config = config or configuration.get_config()
        xml_root = _get_xml_root(xml_root, xml_str, xml_file)
        submit_config = SubmitConfig(xml_root, config, **kwargs)
        session = session or utils.get_session(submit_config.credentials, config)
        submit_response = submit(xml_root, submit_config, session, dry_run=dry_run, **kwargs)
    except Dump2PolarionException as err:
        logger.error(err)
        return None

    valid_response = submit_response.validate_response()
    if not valid_response or kwargs.get("no_verify"):
        return submit_response.response

    response = verify_submit(
        session,
        submit_config.queue_url,
        submit_config.log_url,
        submit_response.job_ids,
        timeout=kwargs.get("verify_timeout"),
        log_file=kwargs.get("log_file"),
    )

    return response
