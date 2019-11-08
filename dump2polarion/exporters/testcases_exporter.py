"""
Creates a Testcase XML file for submitting to the Polarion Importer.

Example of input testcases_data:
testcases_data = [
    {
        "id": "ITEM01",
        "title": "test_manual",
        "description": "Manual tests with all supported fields.",
        "approver-ids": "bossman mkourim:approved",
        "assignee": "mkourim",
        "dueDate": "2018-09-30",
        "initialEstimate": "1/4h",
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
        "linkedWorkItems": "ITEM01",
        "status": "proposed",
    },
    {
        "title": "test_minimal_param",
        "params": ["param1", "param2"],
        "linkedWorkItems": [{"id": "ITEM01", "role": "derived_from"}],
    },
]
"""

import datetime
import logging
import re
from typing import Callable, Dict, Optional, Tuple

from lxml import etree

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters import transform_projects

LOGGER = logging.getLogger(__name__)


class TestcaseTransform:
    """Transform testcase data and fill in default keys and values."""

    TESTCASE_DATA = {
        "approver-ids": None,
        "assignee-id": None,
        "due-date": None,
        "id": None,
        "initial-estimate": None,
        "status-id": None,
    }  # type: Dict[str, Optional[str]]

    FIELD_MAPPING = {
        "assignee-id": "assignee",
        "due-date": "dueDate",
        "initial-estimate": "initialEstimate",
        "status-id": "status",
        "linked-work-items": "linkedWorkItems",
    }  # type: Dict[str, Optional[str]]

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
    }  # type: Dict[str, Optional[str]]

    def __init__(self, config: dict, transform_func: Optional[Callable] = None) -> None:
        self.config = config
        self._transform_func = transform_func or transform_projects.get_testcases_transform(config)

        default_fields = self.config.get("default_fields") or {}
        default_fields = {k: utils.get_unicode_str(v) for k, v in default_fields.items() if v}
        self.default_fields = utils.sorted_dict(default_fields)

    def _fill_project_defaults(self, testcase_data: dict) -> dict:
        filled = self.default_fields.copy()
        filled.update(testcase_data)
        return filled

    def _run_transform_func(self, testcase_data: dict) -> dict:
        """Call transform function on testcase data."""
        if self._transform_func:
            testcase_data = self._transform_func(testcase_data)
        return testcase_data or {}

    def _fill_polarion_fields(self, testcase_data: dict) -> dict:
        """Set importer field value from polarion field if available."""
        for importer_field, polarion_field in self.FIELD_MAPPING.items():
            polarion_value = testcase_data.get(polarion_field)
            xml_value = testcase_data.get(importer_field)
            if polarion_value and not xml_value:
                testcase_data[importer_field] = polarion_value
        return testcase_data

    def _fill_defaults(self, testcase_data: dict) -> dict:
        for defaults in self.TESTCASE_DATA, self.CUSTOM_FIELDS:
            for key, value in defaults.items():
                if value and not testcase_data.get(key):
                    testcase_data[key] = value
        return testcase_data

    def transform(self, testcase_data: dict) -> dict:
        """Transform testcase data."""
        testcase_data = self._fill_project_defaults(testcase_data)
        testcase_data = self._fill_polarion_fields(testcase_data)
        testcase_data = self._run_transform_func(testcase_data)
        if not testcase_data:
            return {}

        testcase_data = self._fill_defaults(testcase_data)
        return testcase_data


class TestcaseExport:
    """Export testcases data into XML representation."""

    def __init__(
        self, testcases_data: dict, config: dict, transform_func: Optional[Callable] = None
    ):
        self.testcases_data = testcases_data
        self.config = config
        self._lookup_prop = ""
        self.testcases_transform = TestcaseTransform(config, transform_func)

        self.known_custom_fields = set(self.testcases_transform.CUSTOM_FIELDS)
        self.known_custom_fields.update(self.config.get("custom_fields") or ())

        self._compiled_whitelist = None
        self._compiled_blacklist = None
        if self.config.get("whitelisted_tests"):
            self._compiled_whitelist = re.compile(
                "(" + ")|(".join(self.config.get("whitelisted_tests", "")) + ")"
            )
        if self.config.get("blacklisted_tests"):
            self._compiled_blacklist = re.compile(
                "(" + ")|(".join(self.config.get("blacklisted_tests", "")) + ")"
            )

    def _top_element(self) -> etree.Element:
        """Return top XML element."""
        attrs = {"project-id": self.config["polarion-project-id"]}
        top = etree.Element("testcases", attrs)
        return top

    def _properties_element(self, parent_element: etree.Element) -> etree.Element:
        """Return properties XML element."""
        testcases_properties = etree.SubElement(parent_element, "properties")

        testcases_properties_conf = self.config.get("testcase_import_properties") or {}
        for name, value in sorted(testcases_properties_conf.items()):
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

    def _fill_lookup_prop(self, testcases_properties: dict) -> None:
        """Fill the polarion-lookup-method property."""
        if not self._lookup_prop:
            raise Dump2PolarionException("Failed to set the 'polarion-lookup-method' property")

        etree.SubElement(
            testcases_properties, "property", {"name": "lookup-method", "value": self._lookup_prop}
        )

    def _set_lookup_prop(self, testcase_data: dict) -> None:
        """Set lookup property based on processed testcases if not configured."""
        if self._lookup_prop:
            return

        if testcase_data.get("id"):
            self._lookup_prop = "id"
        elif testcase_data.get("title"):
            self._lookup_prop = "name"
        else:
            return

        LOGGER.debug("Setting lookup method for testcases to `%s`", self._lookup_prop)

    def _check_lookup_prop(self, testcase_data: dict) -> bool:
        """Check that selected lookup property can be used for this testcase."""
        if not self._lookup_prop:
            return False

        if not testcase_data.get("id") and self._lookup_prop != "name":
            return False
        if not testcase_data.get("title") and self._lookup_prop == "name":
            return False
        return True

    def _get_testcase_id(self, testcase_data: dict) -> Optional[str]:
        """Return testcase id when possible."""
        testcase_id = testcase_data.get("id")
        if testcase_id:
            return testcase_id
        if self._lookup_prop != "name":
            return None
        return testcase_data.get("title")

    def _classify_data(self, testcase_data: dict) -> Tuple[dict, dict]:
        attrs, custom_fields = {}, {}

        for key, value in testcase_data.items():
            if not value:
                continue
            if key in self.testcases_transform.TESTCASE_DATA:
                attrs[key] = value
            elif key in self.known_custom_fields:
                custom_fields[key] = value

        return attrs, custom_fields

    @staticmethod
    def _add_test_steps(parent: etree.Element, testcase_data: dict) -> None:
        steps = testcase_data.get("testSteps")
        results = testcase_data.get("expectedResults") or {}
        params = testcase_data.get("params") or ()
        test_steps = etree.SubElement(parent, "test-steps")

        if steps and testcase_data["caseautomation"] != "automated":
            for index, step in enumerate(steps):
                test_step = etree.SubElement(test_steps, "test-step")
                test_step_col = etree.SubElement(test_step, "test-step-column", id="step")
                test_step_col.text = utils.get_unicode_str(step)

                test_res_col = etree.SubElement(test_step, "test-step-column", id="expectedResult")
                try:
                    test_res_col.text = utils.get_unicode_str(results[index])
                except IndexError:
                    test_res_col.text = ""
        else:
            test_step = etree.SubElement(test_steps, "test-step")
            test_step_col = etree.SubElement(test_step, "test-step-column", id="step")
            for param in params:
                param_el = etree.Element("parameter", name=param, scope="local")
                test_step_col.append(param_el)

    @staticmethod
    def _add_linked_items(parent: etree.Element, testcase_data: dict) -> None:
        linked_items = testcase_data.get("linked-items") or testcase_data.get("linked-work-items")
        if not linked_items:
            return
        if isinstance(linked_items, str) and "," in linked_items or " " in linked_items:
            # multiple unprocessed linked items (should be list already), skip them
            return
        if isinstance(linked_items, (dict, str)):
            linked_items = [linked_items]

        linked_work_items = etree.SubElement(parent, "linked-work-items")
        for work_item in linked_items:
            if isinstance(work_item, str):
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
    def _fill_custom_fields(parent: etree.Element, custom_fields: dict) -> None:
        if not custom_fields:
            return

        custom_fields_el = etree.SubElement(parent, "custom-fields")
        for field, content in custom_fields.items():
            etree.SubElement(
                custom_fields_el,
                "custom-field",
                utils.sorted_dict({"id": field, "content": utils.get_unicode_str(content)}),
            )

    def _is_whitelisted(self, nodeid: str) -> bool:
        """Check if the nodeid is whitelisted."""
        if not nodeid:
            return True
        if self._compiled_whitelist and self._compiled_whitelist.search(nodeid):
            return True
        if self._compiled_blacklist and self._compiled_blacklist.search(nodeid):
            return False
        return True

    def _testcase_element(self, parent_element: etree.Element, testcase_data: dict) -> None:
        """Add testcase XML element."""
        nodeid = testcase_data.get("nodeid", "")
        if not self._is_whitelisted(nodeid):
            LOGGER.debug("Skipping blacklisted node: %s", nodeid)
            return

        testcase_data = self.testcases_transform.transform(testcase_data)
        if not testcase_data:
            return

        testcase_title = testcase_data.get("title")
        self._set_lookup_prop(testcase_data)
        if not self._check_lookup_prop(testcase_data):
            LOGGER.warning(
                "Skipping testcase `%s`, data missing for selected lookup method",
                testcase_data.get("id") or testcase_title,
            )
            return

        # make sure that ID is set even for "name" lookup method
        testcase_data["id"] = self._get_testcase_id(testcase_data)

        attrs, custom_fields = self._classify_data(testcase_data)

        # For testing purposes, the order of fields in resulting XML
        # needs to be always the same.
        attrs = utils.sorted_dict(attrs)
        custom_fields = utils.sorted_dict(custom_fields)

        testcase = etree.SubElement(parent_element, "testcase", attrs)

        title_el = etree.SubElement(testcase, "title")
        title_el.text = utils.get_unicode_str(testcase_title)

        description = testcase_data.get("description")
        if description:
            description_el = etree.SubElement(testcase, "description")
            description_el.text = utils.get_unicode_str(description)

        self._add_test_steps(testcase, testcase_data)
        self._fill_custom_fields(testcase, custom_fields)
        self._add_linked_items(testcase, testcase_data)

    def _fill_testcases(self, parent_element: etree.Element) -> None:
        if not self.testcases_data:
            raise NothingToDoException("Nothing to export")
        for testcase_data in self.testcases_data:
            self._testcase_element(parent_element, testcase_data)

    def export(self) -> str:
        """Return testcases XML."""
        top = self._top_element()
        properties = self._properties_element(top)
        self._fill_testcases(top)
        self._fill_lookup_prop(properties)
        return utils.prettify_xml(top)

    @staticmethod
    def write_xml(xml_str: str, output_file: Optional[str] = None) -> None:
        """Output the XML content into a file."""
        gen_filename = "testcases-{:%Y%m%d%H%M%S}.xml".format(datetime.datetime.now())
        utils.write_xml(xml_str, output_loc=output_file, filename=gen_filename)
