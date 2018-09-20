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

from collections import OrderedDict

import six

from lxml import etree

from dump2polarion import transform, utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException


class TestcaseExport(object):
    """Exports testcases data into XML representation."""

    TESTCASE_DATA = OrderedDict(
        (
            ("approver-ids", None),
            ("assignee-id", None),
            ("due-date", None),
            ("id", None),
            ("initial-estimate", None),
        )
    )
    CUSTOM_FIELDS = OrderedDict(
        (
            ("automation_script", None),
            ("caseautomation", "automated"),
            ("caseimportance", "high"),
            ("caselevel", "component"),
            ("caseposneg", "positive"),
            ("setup", None),
            ("subtype1", "-"),
            ("subtype2", "-"),
            ("tags", None),
            ("teardown", None),
            ("testtype", "functional"),
            ("upstream", None),
        )
    )

    def __init__(self, testcases_data, config, transform_func=None):
        self.testcases_data = testcases_data
        self.config = config
        self._lookup_prop = ""
        self._transform_func = transform_func or transform.get_testcases_transform(config)

    def _transform_result(self, result):
        """Calls transform function on result."""
        if self._transform_func:
            result = self._transform_func(result)
        return result or None

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

    def _check_lookup_prop(self, testcase_id, testcase_title):
        """Checks that selected lookup property can be used for this testcase."""
        if self._lookup_prop:
            if not testcase_id and self._lookup_prop != "name":
                return None
            if not testcase_title and self._lookup_prop == "name":
                return None
        else:
            if testcase_id:
                self._lookup_prop = "id"
            elif testcase_title:
                self._lookup_prop = "name"
        return True

    def _classify_data(self, testcase_data):
        attrs = OrderedDict()
        custom_fields = OrderedDict()

        for key, value in six.iteritems(testcase_data):
            if not value:
                continue
            if key in self.TESTCASE_DATA:
                attrs[key] = value
            elif key in self.CUSTOM_FIELDS:
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
            etree.SubElement(custom_fields_el, "custom-field", {"id": field, "content": content})

    def _testcase_element(self, parent_element, testcase_data):
        """Adds testcase XML element."""
        testcase_data = self._transform_result(testcase_data)
        if not testcase_data:
            return

        title = testcase_data.get("title")
        testcase_id = testcase_data.get("id")
        if not (title or testcase_id):
            return

        if not self._check_lookup_prop(testcase_id, title):
            return

        attrs, custom_fields = self._classify_data(testcase_data)
        attrs, custom_fields = self._fill_defaults(attrs, custom_fields)

        testcase = etree.SubElement(parent_element, "testcase", attrs)

        title_el = etree.SubElement(testcase, "title")
        title_el.text = title

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
