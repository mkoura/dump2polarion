# -*- coding: utf-8 -*-
"""
Creates a Testcase XML file for submitting to the Polarion Importer.

Example of input testcases_data:
testcases_data = [
    {
        "id": "ITEM01",
        "title": "test_manual",
        "description": "Manual tests with all supported fields.",
        "approver-ids": "mkourim:approved",
        "assignee-id": "mkourim",
        "due-date": "2018-09-30",
        "initial-estimate": "1/4h",
        "caseautomation": "manualonly",
        "caseimportance": "high",
        "caselevel": "component",
        "caseposneg": "positive",
        "testtype": "functional",
        "subtype1": "-",
        "subtype2": "-",
        "upstream": "yes",
        "tags": "tag1, tag2",
        "setup": "Do this first",
        "teardown": "Clean up",
        "automation_script": "https://gitlab.com/foo",
        "testSteps": ["step1", "step2"],
        "expectedResults": ["result1", "result2"],
        "linked-items": "ITEM01",
    },
    {
        "title": "test_minimal_param",
        "params": ["param1", "param2"],
        "linked-items": [{"id": "ITEM01", "role": "derived_from"}],
    },
]
"""

from __future__ import absolute_import, unicode_literals

import datetime
import logging
import re
from collections import OrderedDict

import six
from lxml import etree

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters import transform_projects

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class TestcaseExport(object):
    """Exports testcases data into XML representation."""

    TESTCASE_DATA = {
        "approver-ids": None,
        "assignee-id": None,
        "due-date": None,
        "id": None,
        "initial-estimate": None,
    }

    CUSTOM_FIELDS = {
        "arch": None,
        "automation_script": None,
        "caseautomation": "automated",
        "casecomponent": None,
        "caseimportance": "high",
        "caselevel": "component",
        "caseposneg": "positive",
        "customerscenario": None,
        "endsin": None,
        "legacytest": None,
        "multiproduct": None,
        "reqverify": None,
        "setup": None,
        "startsin": None,
        "subcomponent": None,
        "subtype1": "-",
        "subtype2": "-",
        "tags": None,
        "teardown": None,
        "testtier": None,
        "testtype": "functional",
        "upstream": None,
    }

    def __init__(self, testcases_data, config, transform_func=None):
        self.testcases_data = testcases_data
        self.config = config
        self._lookup_prop = ""
        self._transform_func = transform_func or transform_projects.get_testcases_transform(config)

        default_fields = self.config.get("default_fields") or {}
        default_fields = [
            (key, utils.get_unicode_str(value)) for key, value in default_fields.items() if value
        ]
        default_fields.sort()
        self.default_fields = OrderedDict(default_fields)

        self.known_custom_fields = set(self.CUSTOM_FIELDS)
        self.known_custom_fields.update(self.config.get("custom_fields") or ())

        self._compiled_whitelist = None
        self._compiled_blacklist = None
        if self.config.get("whitelisted_tests"):
            self._compiled_whitelist = re.compile(
                "(" + ")|(".join(self.config.get("whitelisted_tests")) + ")"
            )
        if self.config.get("blacklisted_tests"):
            self._compiled_blacklist = re.compile(
                "(" + ")|(".join(self.config.get("blacklisted_tests")) + ")"
            )

    def _transform_testcase(self, testcase_data):
        """Calls transform function on testcase data."""
        if self._transform_func:
            testcase_data = self._transform_func(testcase_data)
        return testcase_data or None

    def _top_element(self):
        """Returns top XML element."""
        attrs = {"project-id": self.config["polarion-project-id"]}
        top = etree.Element("testcases", attrs)
        return top

    def _properties_element(self, parent_element):
        """Returns properties XML element."""
        testcases_properties = etree.SubElement(parent_element, "properties")

        testcases_properties_conf = self.config.get("testcase_import_properties") or {}
        for name, value in sorted(six.iteritems(testcases_properties_conf)):
            if name == "lookup-method":
                lookup_prop = str(value).lower()
                if lookup_prop not in ("id", "name", "custom"):
                    raise Dump2PolarionException(
                        "Invalid value '{}' for the 'lookup-method' property".format(str(value))
                    )
                self._lookup_prop = lookup_prop
            else:
                etree.SubElement(
                    testcases_properties, "property", {"name": name, "value": str(value)}
                )

        return testcases_properties

    def _fill_lookup_prop(self, testcases_properties):
        """Fills the polarion-lookup-method property."""
        if not self._lookup_prop:
            raise Dump2PolarionException("Failed to set the 'polarion-lookup-method' property")

        etree.SubElement(
            testcases_properties, "property", {"name": "lookup-method", "value": self._lookup_prop}
        )

    def _set_lookup_prop(self, testcase_data):
        """Set lookup property based on processed testcases if not configured."""
        if self._lookup_prop:
            return

        if testcase_data.get("id"):
            self._lookup_prop = "id"
        elif testcase_data.get("title"):
            self._lookup_prop = "name"
        else:
            return

        logger.debug("Setting lookup method for testcases to `%s`", self._lookup_prop)

    def _check_lookup_prop(self, testcase_data):
        """Checks that selected lookup property can be used for this testcase."""
        if not self._lookup_prop:
            return False

        if not testcase_data.get("id") and self._lookup_prop != "name":
            return False
        if not testcase_data.get("title") and self._lookup_prop == "name":
            return False
        return True

    def _get_testcase_id(self, testcase_data):
        """Returns testcase id when possible."""
        testcase_id = testcase_data.get("id")
        if testcase_id:
            return testcase_id
        if self._lookup_prop != "name":
            return None
        return testcase_data.get("title")

    def _classify_data(self, testcase_data):
        attrs, custom_fields = {}, {}

        for key, value in six.iteritems(testcase_data):
            if not value:
                continue
            if key in self.TESTCASE_DATA:
                attrs[key] = value
            elif key in self.known_custom_fields:
                custom_fields[key] = value

        return attrs, custom_fields

    def _fill_defaults(self, attrs, custom_fields):
        for key, value in six.iteritems(self.TESTCASE_DATA):
            if value and not attrs.get(key):
                attrs[key] = value
        for key, value in six.iteritems(self.CUSTOM_FIELDS):
            if value and not custom_fields.get(key):
                custom_fields[key] = value
        return attrs, custom_fields

    @staticmethod
    def _add_test_steps(parent, testcase_data):
        steps = testcase_data.get("testSteps")
        results = testcase_data.get("expectedResults")
        params = testcase_data.get("params") or ()
        test_steps = etree.SubElement(parent, "test-steps")

        if steps and testcase_data["caseautomation"] != "automated":
            for index, step in enumerate(steps):
                test_step = etree.SubElement(test_steps, "test-step")
                test_step_col = etree.SubElement(test_step, "test-step-column", id="step")
                test_step_col.text = step

                test_res_col = etree.SubElement(test_step, "test-step-column", id="expectedResult")
                try:
                    test_res_col.text = results[index]
                except IndexError:
                    test_res_col.text = ""
        else:
            test_step = etree.SubElement(test_steps, "test-step")
            test_step_col = etree.SubElement(test_step, "test-step-column", id="step")
            for param in params:
                param_el = etree.Element("parameter", name=param, scope="local")
                test_step_col.append(param_el)

    @staticmethod
    def _add_linked_items(parent, testcase_data):
        linked_items = testcase_data.get("linked-items") or testcase_data.get("linked-work-items")
        if not linked_items:
            return
        if isinstance(linked_items, (dict, six.string_types)):
            linked_items = [linked_items]

        linked_work_items = etree.SubElement(parent, "linked-work-items")
        for work_item in linked_items:
            if isinstance(work_item, six.string_types):
                work_item_id = work_item
                work_item_role = "verifies"
            else:
                work_item_id = work_item.get("id")
                work_item_role = work_item.get("role") or "verifies"

            if not work_item_id:
                continue

            work_item_el = etree.SubElement(linked_work_items, "linked-work-item")
            work_item_el.attrib["workitem-id"] = work_item_id
            work_item_el.attrib["role-id"] = work_item_role

            lookup_method = testcase_data.get("linked-items-lookup-method")
            if lookup_method in ("name", "id"):
                work_item_el.attrib["lookup-method"] = lookup_method

    @staticmethod
    def _fill_custom_fields(parent, custom_fields):
        if not custom_fields:
            return

        custom_fields_el = etree.SubElement(parent, "custom-fields")
        for field, content in six.iteritems(custom_fields):
            etree.SubElement(
                custom_fields_el,
                "custom-field",
                {"id": field, "content": utils.get_unicode_str(content)},
            )

    def _fill_project_defaults(self, testcase_data):
        filled = self.default_fields.copy()
        filled.update(testcase_data)
        return filled

    def _fill_automation_repo(self, testcase_data):
        repo_address = self.config.get("repo_address")
        automation_script = testcase_data.get("automation_script")
        if not (repo_address and automation_script):
            return
        # The master here should probably link the latest "commit" eventually
        testcase_data["automation_script"] = "{}/blob/master/{}".format(
            repo_address, automation_script
        )

    def _is_whitelisted(self, nodeid):
        """Checks if the nodeid is whitelisted."""
        if not nodeid:
            return True
        if self._compiled_whitelist and self._compiled_whitelist.search(nodeid):
            return True
        if self._compiled_blacklist and self._compiled_blacklist.search(nodeid):
            return False
        return True

    def _testcase_element(self, parent_element, testcase_data):
        """Adds testcase XML element."""
        nodeid = testcase_data.get("nodeid")
        if not self._is_whitelisted(nodeid):
            logger.debug("Skipping blacklisted node: %s", nodeid)
            return
        testcase_data = self._fill_project_defaults(testcase_data)
        self._fill_automation_repo(testcase_data)
        testcase_data = self._transform_testcase(testcase_data)
        if not testcase_data:
            return

        testcase_title = testcase_data.get("title")

        self._set_lookup_prop(testcase_data)
        if not self._check_lookup_prop(testcase_data):
            logger.warning(
                "Skipping testcase `%s`, data missing for selected lookup method",
                testcase_data.get("id") or testcase_title,
            )
            return

        # make sure that ID is set even for "name" lookup method
        testcase_data["id"] = self._get_testcase_id(testcase_data)

        attrs, custom_fields = self._classify_data(testcase_data)
        attrs, custom_fields = self._fill_defaults(attrs, custom_fields)

        # For testing purposes, the order of fields in resulting XML
        # needs to be always the same.
        attrs = OrderedDict(sorted(attrs.items()))
        custom_fields = OrderedDict(sorted(custom_fields.items()))

        testcase = etree.SubElement(parent_element, "testcase", attrs)

        title_el = etree.SubElement(testcase, "title")
        title_el.text = testcase_title

        description = testcase_data.get("description")
        if description:
            description_el = etree.SubElement(testcase, "description")
            description_el.text = description

        self._add_test_steps(testcase, testcase_data)
        self._fill_custom_fields(testcase, custom_fields)
        self._add_linked_items(testcase, testcase_data)

    def _fill_testcases(self, parent_element):
        if not self.testcases_data:
            raise NothingToDoException("Nothing to export")
        for testcase_data in self.testcases_data:
            self._testcase_element(parent_element, testcase_data)

    def export(self):
        """Returns testcases XML."""
        top = self._top_element()
        properties = self._properties_element(top)
        self._fill_testcases(top)
        self._fill_lookup_prop(properties)
        return utils.prettify_xml(top)

    @staticmethod
    def write_xml(xml, output_file=None):
        """Outputs the XML content into a file."""
        gen_filename = "testcases-{:%Y%m%d%H%M%S}.xml".format(datetime.datetime.now())
        utils.write_xml(xml, output_loc=output_file, filename=gen_filename)
