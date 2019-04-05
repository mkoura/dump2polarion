# -*- coding: utf-8 -*-
"""
Functions for transforming results per Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the test case to desired value.
"""

from __future__ import absolute_import, unicode_literals

import copy
import logging
import re

from dump2polarion.exporters import transform
from dump2polarion.exporters.verdicts import Verdicts

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def set_cfme_caselevel(testcase, caselevels):
    """Converts tier to caselevel."""
    tier = testcase.get("caselevel")
    if tier is None:
        return

    try:
        caselevel = caselevels[int(tier)]
    except IndexError:
        # invalid value
        caselevel = "component"
    except ValueError:
        # there's already string value
        return

    testcase["caselevel"] = caselevel


def get_xunit_transform_cfme(config):
    """Return result transformation function for CFME."""
    skip_searches = [
        "SKIPME:",
        "Skipping due to these blockers",
        "BZ ?[0-9]+",
        "GH ?#?[0-9]+",
        "GH#ManageIQ",
    ]
    skips = re.compile("(" + ")|(".join(skip_searches) + ")")

    parametrize = config.get("cfme_parametrize", False)

    def results_transform(result):
        """Results transform for CFME."""
        verdict = result.get("verdict")
        if not verdict:
            return None

        result = copy.deepcopy(result)

        transform.setup_parametrization(result, parametrize)
        transform.include_class_in_title(result)
        transform.insert_source_info(result)

        verdict = verdict.strip().lower()
        # we want to submit PASS and WAIT results
        if verdict in Verdicts.PASS + Verdicts.WAIT:
            return result
        comment = result.get("comment")
        # ... and SKIP results where there is a good reason (blocker etc.)
        if verdict in Verdicts.SKIP and comment and skips.search(comment):
            # found reason for skip
            result["comment"] = comment.replace("SKIPME: ", "").replace("SKIPME", "")
            return result
        if verdict in Verdicts.FAIL and comment and "FAILME" in comment:
            result["comment"] = comment.replace("FAILME: ", "").replace("FAILME", "")
            return result
        # we don't want to report this result if here
        return None

    return results_transform


def get_testcases_transform_cfme(config):
    """Return test cases transformation function for CFME."""

    parametrize = config.get("cfme_parametrize", False)
    run_id = config.get("cfme_run_id")

    caselevels = config.get("docstrings") or {}
    caselevels = caselevels.get("valid_values") or {}
    caselevels = caselevels.get("caselevel") or []

    def testcase_transform(testcase):
        """Test cases transform for CFME."""
        testcase = copy.deepcopy(testcase)

        transform.setup_parametrization(testcase, parametrize)
        set_cfme_caselevel(testcase, caselevels)
        transform.preformat_plain_description(testcase)
        transform.add_unique_runid(testcase, run_id)
        transform.add_automation_link(testcase)

        return testcase

    return testcase_transform


# pylint: disable=unused-argument
def get_requirements_transform_cfme(config):
    """Return requirement transformation function for CFME."""

    def requirement_transform(requirement):
        """Requirements transform for CFME."""
        requirement = copy.deepcopy(requirement)

        if "id" in requirement:
            del requirement["id"]

        return requirement

    return requirement_transform


# pylint: disable=unused-argument
def get_xunit_transform_cmp(config):
    """Return result transformation function for CFME."""
    skip_searches = [
        "SKIPME:",
        "Skipping due to these blockers",
        "BZ ?[0-9]+",
        "GH ?#?[0-9]+",
        "GH#ManageIQ",
    ]
    skips = re.compile("(" + ")|(".join(skip_searches) + ")")

    def results_transform(result):
        """Results transform for CMP."""
        verdict = result.get("verdict")
        if not verdict:
            return None

        result = copy.deepcopy(result)

        # don't parametrize if not specifically configured
        if result.get("params"):
            del result["params"]

        classname = result.get("classname", "")
        if classname:
            # we don't need to pass classnames?
            del result["classname"]

        # if the "test_id" property is present, use it as test case ID
        test_id = result.get("test_id", "")
        if test_id:
            result["id"] = test_id

        verdict = verdict.strip().lower()
        # we want to submit PASS and WAIT results
        if verdict in Verdicts.PASS + Verdicts.WAIT:
            return result
        comment = result.get("comment")
        # ... and SKIP results where there is a good reason (blocker etc.)
        if verdict in Verdicts.SKIP and comment and skips.search(comment):
            # found reason for skip
            result["comment"] = comment.replace("SKIPME: ", "").replace("SKIPME", "")
            return result
        if verdict in Verdicts.FAIL and comment and "FAILME" in comment:
            result["comment"] = comment.replace("FAILME: ", "").replace("FAILME", "")
            return result
        # we don't want to report this result if here
        return None

    return results_transform


# pylint: disable=unused-argument
def get_requirements_transform_cloudtp(config):
    """Return requirement transformation function for CLOUDTP."""

    def requirement_transform(requirement):
        """Requirements transform for CLOUDTP."""
        requirement = copy.deepcopy(requirement)

        if "id" in requirement:
            del requirement["id"]
        # TODO: testing purposes, remove once ready
        if not requirement.get("assignee-id"):
            requirement["assignee-id"] = "mkourim"
        if not requirement.get("approver-ids"):
            requirement["approver-ids"] = "mkourim:approved"

        return requirement

    return requirement_transform


PROJECT_MAPPING_XUNIT = {
    "RHCF3": get_xunit_transform_cfme,
    "CMP": get_xunit_transform_cmp,
    "CLOUDTP": get_xunit_transform_cfme,
}

PROJECT_MAPPING_TESTCASES = {"RHCF3": get_testcases_transform_cfme}

PROJECT_MAPPING_REQ = {
    "RHCF3": get_requirements_transform_cfme,
    "CLOUDTP": get_requirements_transform_cloudtp,
}


def get_xunit_transform(config):
    """Returns results transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of results data according to requirements
    of the specific project.

    When no results data are returned, this result will be ignored
    and will not be written to the resulting XML.
    """

    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_XUNIT:
        return PROJECT_MAPPING_XUNIT[project](config)
    return None


def get_testcases_transform(config):
    """Returns test cases transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of test cases data according to requirements
    of the specific project.

    When no test cases data are returned, this test case will be ignored
    and will not be written to the resulting XML.
    """

    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_TESTCASES:
        return PROJECT_MAPPING_TESTCASES[project](config)
    return None


def get_requirements_transform(config):
    """Returns requirements transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of requirements data according to needs
    of the specific project.

    When no requirements data are returned, this requirement will be ignored
    and will not be written to the resulting XML.
    """

    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_REQ:
        return PROJECT_MAPPING_REQ[project](config)
    return None
