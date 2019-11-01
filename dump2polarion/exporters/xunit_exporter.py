"""
Dump testcases results to XUnit file for submitting to the Polarion XUnit Importer.

Example of input tests_records:
tests_records = ImportedData(
    results=[
        {
            "title": "test_post_single[vim-common-2:7.4.160-1.el7.x86_64.rpm]",
            "classname": "vmaas.tests.test_packages.TestPackagesQuery",
            "verdict": "passed",
            "time": "0.00890207290649414",
            "file": "vmaas/tests/test_packages.py",
            "params": {"pkg": "some_package"},
        }
    ],
    testrun=None,
)
"""

import datetime
import logging
from collections import namedtuple
from typing import Callable, Optional

from lxml import etree

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters import transform_projects
from dump2polarion.exporters.verdicts import Verdicts

ImportedData = namedtuple("ImportedData", "results testrun")

LOGGER = logging.getLogger(__name__)


class XunitExport:
    """Export testcases results into Polarion XUnit."""

    def __init__(
        self,
        testrun_id: str,
        tests_records: ImportedData,
        config: dict,
        transform_func: Optional[Callable] = None,
    ) -> None:
        self.testrun_id = testrun_id
        self.tests_records = tests_records
        self.config = config
        self._lookup_prop = ""
        self._transform_func = transform_func or transform_projects.get_xunit_transform(config)

    def _top_element(self) -> etree.Element:
        """Return top XML element."""
        top = etree.Element("testsuites")
        comment = etree.Comment("Generated for testrun {}".format(self.testrun_id))
        top.append(comment)
        return top

    def _properties_element(self, parent_element: etree.Element) -> etree.Element:
        """Return properties XML element."""
        testsuites_properties = etree.SubElement(parent_element, "properties")

        etree.SubElement(
            testsuites_properties,
            "property",
            {"name": "polarion-testrun-id", "value": str(self.testrun_id)},
        )
        etree.SubElement(
            testsuites_properties,
            "property",
            {"name": "polarion-project-id", "value": str(self.config["polarion-project-id"])},
        )

        for name, value in sorted(self.config["xunit_import_properties"].items()):
            if name == "polarion-lookup-method":
                lookup_prop = str(value).lower()
                if lookup_prop not in ("id", "name", "custom"):
                    raise Dump2PolarionException(
                        "Invalid value '{}' for the 'polarion-lookup-method' property".format(
                            str(value)
                        )
                    )
                self._lookup_prop = lookup_prop
            elif name in ("polarion-testrun-id", "polarion-project-id"):
                # this was already set
                continue
            else:
                etree.SubElement(
                    testsuites_properties, "property", {"name": name, "value": str(value)}
                )

        return testsuites_properties

    def _fill_lookup_prop(self, testsuites_properties: etree.Element) -> None:
        """Fill the polarion-lookup-method property."""
        if not self._lookup_prop:
            raise Dump2PolarionException("Failed to set the 'polarion-lookup-method' property")

        etree.SubElement(
            testsuites_properties,
            "property",
            {"name": "polarion-lookup-method", "value": self._lookup_prop},
        )

    def _testsuite_element(self, parent_element: etree.Element) -> etree.Element:
        """Return testsuite XML element."""
        testsuite = etree.SubElement(
            parent_element,
            "testsuite",
            {
                "name": "Import for {} - {} testrun".format(
                    self.config["polarion-project-id"], self.testrun_id
                )
            },
        )
        return testsuite

    @staticmethod
    def _fill_verdict(verdict: str, result: dict, testcase: etree.Element, records: dict) -> None:
        # XUnit Pass maps to Passed in Polarion
        if verdict in Verdicts.PASS:
            records["passed"] += 1
        # XUnit Failure maps to Failed in Polarion
        elif verdict in Verdicts.FAIL:
            records["failures"] += 1
            verdict_data = {"type": "failure"}
            if result.get("comment"):
                verdict_data["message"] = utils.get_unicode_str(result["comment"])
            etree.SubElement(testcase, "failure", utils.sorted_dict(verdict_data))
        # XUnit Error maps to Blocked in Polarion
        elif verdict in Verdicts.SKIP:
            records["skipped"] += 1
            verdict_data = {"type": "error"}
            if result.get("comment"):
                verdict_data["message"] = utils.get_unicode_str(result["comment"])
            etree.SubElement(testcase, "error", utils.sorted_dict(verdict_data))
        # XUnit Skipped maps to Waiting in Polarion
        elif verdict in Verdicts.WAIT:
            records["waiting"] += 1
            verdict_data = {"type": "skipped"}
            if result.get("comment"):
                verdict_data["message"] = utils.get_unicode_str(result["comment"])
            etree.SubElement(testcase, "skipped", utils.sorted_dict(verdict_data))

    def _transform_result(self, result: dict) -> dict:
        """Call transform function on result."""
        if self._transform_func:
            result = self._transform_func(result)
        return result or {}

    @staticmethod
    def _get_verdict(result: dict):
        """Get verdict of the testcase."""
        verdict = result.get("verdict")
        if not verdict:
            return None
        verdict = verdict.strip().lower()
        if verdict not in Verdicts.PASS + Verdicts.FAIL + Verdicts.SKIP + Verdicts.WAIT:
            return None
        return verdict

    def _set_lookup_prop(self, result_data: dict) -> None:
        """Set lookup property based on processed testcases if not configured."""
        if self._lookup_prop:
            return

        if result_data.get("id"):
            self._lookup_prop = "id"
        elif result_data.get("title"):
            self._lookup_prop = "name"
        else:
            return

        LOGGER.debug("Setting lookup method for xunit to `%s`", self._lookup_prop)

    def _check_lookup_prop(self, result_data: dict) -> bool:
        """Check that selected lookup property can be used for this testcase."""
        if not self._lookup_prop:
            return False

        if not result_data.get("id") and self._lookup_prop != "name":
            return False
        if not result_data.get("title") and self._lookup_prop == "name":
            return False
        return True

    @staticmethod
    def _testcase_element(
        parent_element: etree.Element,
        result: dict,
        records: dict,
        testcase_id: Optional[str],
        testcase_title: Optional[str],
    ) -> etree.Element:
        """Create XML element for given testcase result and update testcases records."""
        name = testcase_title or testcase_id
        if not name:
            raise Dump2PolarionException(
                "Neither `testcase_id` not `testcase_title` has valid value."
            )
        testcase_time = float(result.get("time") or result.get("duration") or 0)
        records["time"] += testcase_time

        testcase_data = {"name": name, "time": str(testcase_time)}
        if result.get("classname"):
            testcase_data["classname"] = result["classname"]
        testcase = etree.SubElement(parent_element, "testcase", utils.sorted_dict(testcase_data))
        return testcase

    @staticmethod
    def _fill_out_err(result: dict, testcase: etree.Element) -> None:
        """Add stdout and stderr if present."""
        if result.get("stdout"):
            system_out = etree.SubElement(testcase, "system-out")
            system_out.text = utils.get_unicode_str(result["stdout"])

        if result.get("stderr"):
            system_err = etree.SubElement(testcase, "system-err")
            system_err.text = utils.get_unicode_str(result["stderr"])

    @staticmethod
    def _fill_properties(
        verdict: str,
        result: dict,
        testcase: etree.Element,
        testcase_id: Optional[str],
        testcase_title: Optional[str],
    ) -> None:
        """Add properties into testcase element."""
        id_value = testcase_id or testcase_title
        if not id_value:
            raise Dump2PolarionException(
                "Neither `testcase_id` not `testcase_title` has valid value."
            )
        properties = etree.SubElement(testcase, "properties")
        etree.SubElement(
            properties, "property", {"name": "polarion-testcase-id", "value": id_value}
        )
        if verdict in Verdicts.PASS and result.get("comment"):
            etree.SubElement(
                properties,
                "property",
                {
                    "name": "polarion-testcase-comment",
                    "value": utils.get_unicode_str(result["comment"]),
                },
            )

        params = result.get("params") or {}
        for param, value in params.items():
            etree.SubElement(
                properties,
                "property",
                {
                    "name": "polarion-parameter-{}".format(param),
                    "value": utils.get_unicode_str(value),
                },
            )

    def _gen_testcase(self, parent_element: etree.Element, result: dict, records: dict) -> None:
        """Create record for given testcase result."""
        result = self._transform_result(result)
        if not result:
            return

        verdict = self._get_verdict(result)
        if not verdict:
            LOGGER.warning("Skipping testcase, verdict is missing or invalid")
            return

        testcase_id = result.get("id")
        testcase_title = result.get("title")

        self._set_lookup_prop(result)
        if not self._check_lookup_prop(result):
            LOGGER.warning(
                "Skipping testcase `%s`, data missing for selected lookup method",
                testcase_id or testcase_title,
            )
            return

        testcase = self._testcase_element(
            parent_element, result, records, testcase_id, testcase_title
        )

        self._fill_verdict(verdict, result, testcase, records)
        self._fill_out_err(result, testcase)
        self._fill_properties(verdict, result, testcase, testcase_id, testcase_title)

    def _fill_tests_results(self, testsuite_element: etree.Element) -> None:
        """Create records for all testcases results."""
        if not self.tests_records.results:
            raise NothingToDoException("Nothing to export")

        records = {"passed": 0, "skipped": 0, "failures": 0, "waiting": 0, "time": 0.0}
        for testcase_result in self.tests_records.results:
            self._gen_testcase(testsuite_element, testcase_result, records)

        tests_num = (
            records["passed"] + records["skipped"] + records["failures"] + records["waiting"]
        )

        if tests_num == 0:
            raise NothingToDoException("Nothing to export")

        testsuite_element.set("errors", str(records["skipped"]))
        testsuite_element.set("failures", str(records["failures"]))
        testsuite_element.set("skipped", str(records["waiting"]))
        testsuite_element.set("time", "{:.4f}".format(records["time"]))
        testsuite_element.set("tests", str(tests_num))

    def export(self) -> str:
        """Return XUnit XML."""
        top = self._top_element()
        properties = self._properties_element(top)
        testsuite = self._testsuite_element(top)
        self._fill_tests_results(testsuite)
        self._fill_lookup_prop(properties)
        return utils.prettify_xml(top)

    def write_xml(self, xml_str: str, output_file: Optional[str] = None) -> None:
        """Output the XML content into a file."""
        gen_filename = "testrun_{}-{:%Y%m%d%H%M%S}.xml".format(
            self.testrun_id, datetime.datetime.now()
        )
        utils.write_xml(xml_str, output_loc=output_file, filename=gen_filename)
