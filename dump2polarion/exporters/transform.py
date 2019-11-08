"""Helper functions for transforming results."""

import hashlib
import logging
import os
import re
import urllib.parse
from typing import Optional

from docutils.core import publish_parts

from dump2polarion.exporters.verdicts import Verdicts

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

TEST_PARAM_RE = re.compile(r"\[.*\]")


def only_passed_and_wait(result):
    """Return PASS and WAIT results only, skips everything else."""
    verdict = result.get("verdict", "").strip().lower()
    if verdict in Verdicts.PASS + Verdicts.WAIT:
        return result
    return None


def insert_source_info(result):
    """Add info about source of test result if available."""
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
    """Modify result's data according to the parametrization settings."""
    if parametrize:
        # remove parameters from title
        title = result.get("title")
        if title:
            result["title"] = TEST_PARAM_RE.sub("", title)
        # remove parameters also from id if it's identical to title
        if title and result.get("id") == title:
            result["id"] = result["title"]
    else:
        # don't parametrize if not specifically configured
        if "params" in result:
            del result["params"]


def include_class_in_title(result):
    """Make sure that test class is included in "title".

    Applies only to titles derived from test function names, e.g.
    "test_power_parent_service" -> "TestServiceRESTAPI.test_power_parent_service"

    >>> result = {"title": "test_foo", "id": "test_foo", "classname": "foo.bar.baz.TestFoo",
    ...    "file": "foo/bar/baz.py"}
    >>> include_class_in_title(result)
    >>> str(result.get("title"))
    'TestFoo.test_foo'
    >>> str(result.get("id"))
    'TestFoo.test_foo'
    >>> result.get("classname")
    >>> result = {"title": "some title", "id": "test_foo", "classname": "foo.bar.baz.TestFoo",
    ...    "file": "foo/bar/baz.py"}
    >>> include_class_in_title(result)
    >>> str(result.get("title"))
    'some title'
    >>> str(result.get("id"))
    'test_foo'
    """
    classname = result.get("classname", "")
    if not classname:
        return

    filepath = result.get("file", "")
    title = result.get("title")
    if title and title.startswith("test_") and "/" in filepath and "." in classname:
        fname = filepath.split("/")[-1].replace(".py", "")
        last_classname = classname.split(".")[-1]
        # last part of classname is not file name
        if fname != last_classname and last_classname not in title:
            result["title"] = "{}.{}".format(last_classname, title)
        # update also the id if it is identical to original title
        if result.get("id") == title:
            result["id"] = result["title"]

    # we don't need to pass classnames?
    del result["classname"]


def gen_unique_id(string):
    """Generate unique id out of a string.

    >>> gen_unique_id("vmaas_TestClass.test_name")
    '5acc5dc795a620c6b4491b681e5da39c'
    """
    return hashlib.sha1(string.encode("utf-8")).hexdigest()[:32]


def get_testcase_id(testcase, append_str):
    """Return new test case ID.

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
    """Create an HTML version of the RST formatted description."""
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
    """Create a preformatted HTML version of the description."""
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
    """Add run id to the test description.

    The `run_id` runs makes the descriptions unique between imports and force Polarion
    to update every testcase every time.
    """
    testcase["description"] = '{visible}<br id="{invisible}"/>'.format(
        visible=testcase.get("description") or "empty-description-placeholder",
        invisible=run_id or id(add_unique_runid),
    )


def get_full_repo_address(repo_address: Optional[str]):
    """Make sure the repo address is complete path in repository.

    >>> get_full_repo_address("https://gitlab.com/somerepo")
    'https://gitlab.com/somerepo/blob/master/'
    >>> get_full_repo_address("https://github.com/otherrepo/blob/branch/")
    'https://github.com/otherrepo/blob/branch/'
    >>> get_full_repo_address(None)
    """
    if not repo_address:
        return None

    if "/blob/" not in repo_address:
        # the master here should probably link the latest "commit" eventually
        repo_address = "{}/blob/master".format(repo_address)

    # make sure the / is present at the end of address
    repo_address = "{}/".format(repo_address.rstrip("/ "))

    return repo_address


def fill_automation_repo(repo_address: Optional[str], testcase: dict) -> dict:
    """Fill repo address to "automation_script" if missing."""
    automation_script = testcase.get("automation_script")
    if not automation_script:
        return testcase

    if not repo_address:
        del testcase["automation_script"]
        return testcase

    if automation_script.startswith("http"):
        return testcase

    testcase["automation_script"] = urllib.parse.urljoin(repo_address, automation_script)
    return testcase


def add_automation_link(testcase):
    """Append link to automation script to the test description."""
    automation_script = testcase.get("automation_script")
    if not automation_script:
        return testcase

    automation_link = '<a href="{}">Test Source</a>'.format(automation_script)
    testcase["description"] = "{}<br/>{}".format(testcase.get("description") or "", automation_link)
    return testcase
