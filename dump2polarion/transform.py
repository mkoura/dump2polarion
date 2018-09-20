# -*- coding: utf-8 -*-
"""
Functions for validating and transforming results. These are specific per Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the test case to desired value.
"""

from __future__ import absolute_import, unicode_literals

import copy
import hashlib
import re

from dump2polarion.verdicts import Verdicts

TEST_PARAM_RE = re.compile(r"\[.*\]")


def only_passed_and_wait(result):
    """Returns PASS and WAIT results only, skips everything else."""
    verdict = result.get("verdict", "").strip().lower()
    if verdict in Verdicts.PASS + Verdicts.WAIT:
        return result
    return None


def _insert_source_info(result):
    """Adds info about source of test result if available."""
    comment = result.get("comment")
    # don't change comment if it already exists
    if comment:
        return

    source = result.get("source")
    job_name = result.get("job_name")
    run = result.get("run")
    source_list = [source, job_name, run]
    if not all(source_list):
        return

    source_note = "/".join(source_list)
    source_note = "Source: {}".format(source_note)
    result["comment"] = source_note


def _setup_parametrization(result, parametrize):
    """Modifies result's data according to the parametrization settings."""
    parameters = result.get("params", {})

    if parametrize:
        # remove parameters from title
        title = result.get("title")
        if title:
            result["title"] = TEST_PARAM_RE.sub("", title)
    else:
        # don't parametrize if not specifically configured
        if parameters:
            del result["params"]


def _include_class_in_title(result):
    """Makes sure that test class is included in "title".

    e.g. "TestServiceRESTAPI.test_power_parent_service"
    """
    classname = result.get("classname", "")
    if classname:
        filepath = result.get("file", "")
        title = result.get("title")
        if title and "/" in filepath and "." in classname:
            fname = filepath.split("/")[-1].replace(".py", "")
            last_classname = classname.split(".")[-1]
            # last part of classname is not file name
            if fname != last_classname and last_classname not in title:
                result["title"] = "{}.{}".format(last_classname, title)
        # we don't need to pass classnames?
        del result["classname"]


def gen_unique_id(string):
    """Generates unique id out of a string.

    >>> gen_unique_id("vmaas_TestClass.test_name")
    '5acc5dc795a620c6b4491b681e5da39c'
    """
    return hashlib.sha1(string.encode("utf-8")).hexdigest()[:32]


def get_testcase_id(testcase, append_str):
    """Returns new test case ID.

    >>> get_testcase_id({"title": "TestClass.test_name"}, "vmaas_")
    '5acc5dc795a620c6b4491b681e5da39c'
    >>> get_testcase_id({"title": "TestClass.test_name", "id": "TestClass.test_name"}, "vmaas_")
    '5acc5dc795a620c6b4491b681e5da39c'
    >>> str(get_testcase_id({"title": "TestClass.test_name", "id": "test"}, "vmaas_"))
    'test'
    """
    testcase_title = testcase.get("title")
    testcase_id = testcase.get("id")
    if not testcase_id or testcase_title in testcase_id:
        testcase_id = gen_unique_id("{}{}".format(append_str, testcase_title))
    return testcase_id


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

        _setup_parametrization(result, parametrize)
        _include_class_in_title(result)
        _insert_source_info(result)

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


def get_xunit_transform_insights(config):
    """Return result transformation function for Insights."""
    skip_searches = ["SKIPME:", "Skipping due to these blockers", "BZ ?[0-9]+", "GH ?#?[0-9]+"]
    skips = re.compile("(" + ")|(".join(skip_searches) + ")")

    parametrize = config.get("insights_parametrize", False)
    testcase_append = config.get("insights_testcase_append", "")

    def results_transform(result):
        """Results transform for Insights."""
        verdict = result.get("verdict")
        if not verdict:
            return None

        result = copy.deepcopy(result)

        _setup_parametrization(result, parametrize)
        _include_class_in_title(result)
        _insert_source_info(result)

        result["id"] = get_testcase_id(result, testcase_append)

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

    def testcase_transform(testcase):
        """Test cases transform for CFME."""
        testcase = copy.deepcopy(testcase)

        _setup_parametrization(testcase, parametrize)

        return testcase

    return testcase_transform


def get_testcases_transform_insights(config):
    """Return test cases transformation function for Insights."""

    parametrize = config.get("insights_parametrize", False)
    testcase_append = config.get("insights_testcase_append", "")
    seen_ids = []

    def testcase_transform(testcase):
        """Test cases transform for Insights."""
        testcase = copy.deepcopy(testcase)

        _setup_parametrization(testcase, parametrize)

        testcase_id = get_testcase_id(testcase, testcase_append)
        testcase["id"] = testcase_id

        if parametrize and testcase_id in seen_ids:
            return None
        seen_ids.append(testcase_id)

        return testcase

    return testcase_transform


def get_requirements_transform_cfme(config):
    """Return requirement transformation function for CFME."""

    def requirement_transform(requirement):
        """Requirements transform for CFME."""
        requirement = copy.deepcopy(requirement)

        if "id" in requirement:
            del requirement["id"]

        return requirement

    return requirement_transform


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


def get_requirements_transform_insights(config):
    """Return requirement transformation function for Insights."""

    def requirement_transform(requirement):
        """Requirements transform for Insights."""
        requirement = copy.deepcopy(requirement)
        # TODO: append smtg to requirements title?
        # Would require to also modify all linked-items in test cases.

        if "id" in requirement:
            del requirement["id"]

        return requirement

    return requirement_transform


PROJECT_MAPPING_XUNIT = {
    "RHCF3": get_xunit_transform_cfme,
    "CMP": get_xunit_transform_cmp,
    "CLOUDTP": get_xunit_transform_cfme,
    "Insights": get_xunit_transform_insights,
}

PROJECT_MAPPING_TESTCASES = {
    "RHCF3": get_testcases_transform_cfme,
    "Insights": get_testcases_transform_insights,
}

PROJECT_MAPPING_REQ = {
    "RHCF3": get_requirements_transform_cfme,
    "CLOUDTP": get_requirements_transform_cloudtp,
    "Insights": get_requirements_transform_insights,
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
