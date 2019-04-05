# -*- coding: utf-8 -*-
"""
Helper functions for transforming results.
"""

from __future__ import absolute_import, unicode_literals

import hashlib
import logging
import os
import re

from docutils.core import publish_parts

from dump2polarion.exporters.verdicts import Verdicts

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

TEST_PARAM_RE = re.compile(r"\[.*\]")


def only_passed_and_wait(result):
    """Returns PASS and WAIT results only, skips everything else."""
    verdict = result.get("verdict", "").strip().lower()
    if verdict in Verdicts.PASS + Verdicts.WAIT:
        return result
    return None


def insert_source_info(result):
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


def setup_parametrization(result, parametrize):
    """Modifies result's data according to the parametrization settings."""
    if parametrize:
        # remove parameters from title
        title = result.get("title")
        if title:
            result["title"] = TEST_PARAM_RE.sub("", title)
    else:
        # don't parametrize if not specifically configured
        if "params" in result:
            del result["params"]


def include_class_in_title(result):
    """Makes sure that test class is included in "title".

    e.g. "TestServiceRESTAPI.test_power_parent_service"

    >>> result = {"title": "test_foo", "classname": "foo.bar.baz.TestFoo",
    ...    "file": "foo/bar/baz.py"}
    >>> include_class_in_title(result)
    >>> str(result.get("title"))
    'TestFoo.test_foo'
    >>> result.get("classname")
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
    >>> get_testcase_id({"title": "TestClass.test_name", "id": "test_name"}, "vmaas_")
    '5acc5dc795a620c6b4491b681e5da39c'
    >>> get_testcase_id({"title": "some title", "id": "TestClass.test_name"}, "vmaas_")
    '2ea7695b73763331f8a0c4aec75362b8'
    >>> str(get_testcase_id({"title": "some title", "id": "some_id"}, "vmaas_"))
    'some_id'
    """
    testcase_title = testcase.get("title")
    testcase_id = testcase.get("id")
    if not testcase_id or testcase_id.lower().startswith("test"):
        testcase_id = gen_unique_id("{}{}".format(append_str, testcase_title))
    return testcase_id


def parse_rst_description(testcase):
    """Creates an HTML version of the RST formatted description."""
    description = testcase.get("description")

    if not description:
        return

    try:
        with open(os.devnull, "w") as devnull:
            testcase["description"] = publish_parts(
                description,
                writer_name="html",
                settings_overrides={"report_level": 2, "halt_level": 2, "warning_stream": devnull},
            )["html_body"]
    # pylint: disable=broad-except
    except Exception as exp:
        testcase_id = testcase.get("nodeid") or testcase.get("id") or testcase.get("title")
        logger.error("%s: description: %s", str(exp), testcase_id)


def preformat_plain_description(testcase):
    """Creates a preformatted HTML version of the description."""
    description = testcase.get("description")

    if not description:
        return

    # naive approach to removing indent from pytest docstrings
    nodeid = testcase.get("nodeid") or ""
    indent = None
    if "::Test" in nodeid:
        indent = 8 * " "
    elif "::test_" in nodeid:
        indent = 4 * " "

    if indent:
        orig_lines = description.split("\n")
        new_lines = []
        for line in orig_lines:
            if line.startswith(indent):
                line = line.replace(indent, "", 1)
            new_lines.append(line)
        description = "\n".join(new_lines)

    testcase["description"] = "<pre>\n{}\n</pre>".format(description)


def add_unique_runid(testcase, run_id=None):
    """Adds run id to the test description.

    The `run_id` runs makes the descriptions unique between imports and force Polarion
    to update every testcase every time.
    """
    testcase["description"] = '{}<br id="{}"/>'.format(
        testcase.get("description") or "", run_id or id(add_unique_runid)
    )


def add_automation_link(testcase):
    """Appends link to automation script to the test description."""
    automation_link = (
        '<a href="{}">Test Source</a>'.format(testcase["automation_script"])
        if testcase.get("automation_script")
        else ""
    )
    testcase["description"] = "{}<br/>{}".format(testcase.get("description") or "", automation_link)
