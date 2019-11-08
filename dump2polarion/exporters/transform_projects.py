"""
Functions for transforming results per Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the test case to desired value.
"""

import copy
import logging
import re

from dump2polarion.exporters import transform
from dump2polarion.exporters.verdicts import Verdicts

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_xunit_transform_default(config):
    """Return result transformation function."""
    parametrize = config.get("parametrize", False)

    def results_transform(result):
        """Transform results."""
        verdict = result.get("verdict")
        if not verdict:
            return None

        result = copy.deepcopy(result)

        transform.setup_parametrization(result, parametrize)
        transform.include_class_in_title(result)
        transform.insert_source_info(result)

        return result

    return results_transform


def get_testcases_transform_default(config):
    """Return test cases transformation function."""
    parametrize = config.get("parametrize", False)
    use_run_id = config.get("use_run_id", False)
    run_id = config.get("run_id")
    repo_address = transform.get_full_repo_address(config.get("repo_address"))

    def testcase_transform(testcase):
        """Transform test cases."""
        testcase = copy.deepcopy(testcase)

        transform.setup_parametrization(testcase, parametrize)
        transform.fill_automation_repo(repo_address, testcase)
        transform.preformat_plain_description(testcase)
        if use_run_id:
            transform.add_unique_runid(testcase, run_id)
        transform.add_automation_link(testcase)

        return testcase

    return testcase_transform


# pylint: disable=unused-argument
def get_requirements_transform_default(config):  # noqa: D202
    """Return requirement transformation function."""

    def requirement_transform(requirement):
        """Transform requirements."""
        return requirement

    return requirement_transform


def set_cfme_caselevel(testcase, caselevels):
    """Convert tier to caselevel."""
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
        r"bugzilla\.redhat\.com",
        r"github\.com",
    ]
    skips = re.compile("(" + ")|(".join(skip_searches) + ")")

    parametrize = config.get("cfme_parametrize", False)

    def results_transform(result):
        """Transform results for CFME."""
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
    use_run_id = config.get("use_run_id", True)
    run_id = config.get("cfme_run_id")
    repo_address = transform.get_full_repo_address(config.get("repo_address"))

    caselevels = config.get("docstrings") or {}
    caselevels = caselevels.get("valid_values") or {}
    caselevels = caselevels.get("caselevel") or []

    def testcase_transform(testcase):
        """Transform test cases for CFME."""
        testcase = copy.deepcopy(testcase)

        transform.setup_parametrization(testcase, parametrize)
        set_cfme_caselevel(testcase, caselevels)
        transform.fill_automation_repo(repo_address, testcase)
        transform.preformat_plain_description(testcase)
        if use_run_id:
            transform.add_unique_runid(testcase, run_id)
        transform.add_automation_link(testcase)

        return testcase

    return testcase_transform


# pylint: disable=unused-argument
def get_requirements_transform_cfme(config):  # noqa: D202
    """Return requirement transformation function for CFME."""

    def requirement_transform(requirement):
        """Transform requirements for CFME."""
        requirement = copy.deepcopy(requirement)

        if "id" in requirement:
            del requirement["id"]

        return requirement

    return requirement_transform


# pylint: disable=unused-argument
def get_requirements_transform_cloudtp(config):  # noqa: D202
    """Return requirement transformation function for CLOUDTP."""

    def requirement_transform(requirement):
        """Transform requirements for CLOUDTP."""
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
    "CLOUDTP": get_xunit_transform_cfme,
}

PROJECT_MAPPING_TESTCASES = {"RHCF3": get_testcases_transform_cfme}

PROJECT_MAPPING_REQ = {
    "RHCF3": get_requirements_transform_cfme,
    "CLOUDTP": get_requirements_transform_cloudtp,
}


def get_xunit_transform(config):
    """Return results transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of results data according to requirements
    of the specific project.

    When no results data are returned, this result will be ignored
    and will not be written to the resulting XML.
    """
    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_XUNIT:
        return PROJECT_MAPPING_XUNIT[project](config)
    return get_xunit_transform_default(config)


def get_testcases_transform(config):
    """Return test cases transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of test cases data according to requirements
    of the specific project.

    When no test cases data are returned, this test case will be ignored
    and will not be written to the resulting XML.
    """
    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_TESTCASES:
        return PROJECT_MAPPING_TESTCASES[project](config)
    return get_testcases_transform_default(config)


def get_requirements_transform(config):
    """Return requirements transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of requirements data according to needs
    of the specific project.

    When no requirements data are returned, this requirement will be ignored
    and will not be written to the resulting XML.
    """
    project = config["polarion-project-id"]
    if project in PROJECT_MAPPING_REQ:
        return PROJECT_MAPPING_REQ[project](config)
    return get_requirements_transform_default(config)
