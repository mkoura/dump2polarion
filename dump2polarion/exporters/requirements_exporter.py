"""
Creates a Requirement XML file for submitting to the Polarion Importer.

Example of input requirements_data:
requirements_data = [
    {
        "title": "requirement_complete",
        "description": "Complete Requirement",
        "approver-ids": "mkourim:approved",
        "assignee": "mkourim",
        "category-ids": "category_id1, category_id2",
        "dueDate": "2018-09-30",
        "plannedIn": "planned_id1, planned_id2",
        "initialEstimate": "1/4h",
        "priority": "high",
        "severity": "should_have",
        "status": "status_id",
        "reqtype": "functional",
    },
    {
        "title": "requirement_minimal",
    },
]
"""

import datetime
import logging
from typing import Callable, Tuple, Optional, Dict

from lxml import etree

from dump2polarion import utils
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters import transform_projects

LOGGER = logging.getLogger(__name__)


class RequirementTransform:
    """Transform requirement data and fill in default keys and values."""

    REQ_DATA = {
        "approver-ids": None,
        "assignee-id": None,
        "category-ids": None,
        "due-date": None,
        "initial-estimate": None,
        "planned-in-ids": None,
        "priority-id": "high",
        "severity-id": "should_have",
        "status-id": None,
    }  # type: Dict[str, Optional[str]]

    FIELD_MAPPING = {
        "assignee-id": "assignee",
        "due-date": "dueDate",
        "initial-estimate": "initialEstimate",
        "planned-in-ids": "plannedIn",
        "priority-id": "priority",
        "severity-id": "severity",
        "status-id": "status",
    }  # type: Dict[str, Optional[str]]

    CUSTOM_FIELDS = {"reqtype": "functional"}  # type: Dict[str, Optional[str]]

    def __init__(self, config: dict, transform_func: Optional[Callable] = None) -> None:
        self.config = config
        self._transform_func = transform_func or transform_projects.get_requirements_transform(
            config
        )

        default_fields = self.config.get("requirements_default_fields") or {}
        default_fields = {k: utils.get_unicode_str(v) for k, v in default_fields.items() if v}
        self.default_fields = utils.sorted_dict(default_fields)

    def _fill_project_defaults(self, testcase_data: dict) -> dict:
        filled = self.default_fields.copy()
        filled.update(testcase_data)
        return filled

    def _run_transform_func(self, result: dict) -> dict:
        """Call transform function on result."""
        if self._transform_func:
            result = self._transform_func(result)
        return result or {}

    def _fill_polarion_fields(self, req_data: dict) -> dict:
        """Set importer field value from polarion field if available."""
        for importer_field, polarion_field in self.FIELD_MAPPING.items():
            polarion_value = req_data.get(polarion_field)
            xml_value = req_data.get(importer_field)
            if polarion_value and not xml_value:
                req_data[importer_field] = polarion_value
        return req_data

    def _fill_defaults(self, req_data: dict) -> dict:
        for defaults in self.REQ_DATA, self.CUSTOM_FIELDS:
            for key, value in defaults.items():
                if value and not req_data.get(key):
                    req_data[key] = value
        return req_data

    def transform(self, req_data: dict) -> dict:
        """Transform requirement data."""
        req_data = self._fill_project_defaults(req_data)
        req_data = self._fill_polarion_fields(req_data)
        req_data = self._run_transform_func(req_data)
        if not req_data:
            return {}

        title = req_data.get("title")
        if not title:
            LOGGER.warning("Skipping requirement, title is missing")
            return {}

        req_data = self._fill_defaults(req_data)
        return req_data


class RequirementExport:
    """Export requirements data into XML representation."""

    def __init__(
        self, requirements_data: dict, config: dict, transform_func: Optional[Callable] = None
    ) -> None:
        self.requirements_data = requirements_data
        self.config = config
        self._lookup_prop = ""
        self.requirement_transform = RequirementTransform(config, transform_func)

        self.known_custom_fields = set(self.requirement_transform.CUSTOM_FIELDS)
        self.known_custom_fields.update(self.config.get("requirements_custom_fields") or ())

    def _top_element(self) -> etree.Element:
        """Return top XML element."""
        attrs = {"project-id": self.config["polarion-project-id"]}
        document_relative_path = self.config.get("requirements-document-relative-path")
        if document_relative_path:
            attrs["document-relative-path"] = document_relative_path
        top = etree.Element("requirements", utils.sorted_dict(attrs))
        return top

    def _properties_element(self, parent_element: etree.Element) -> etree.Element:
        """Return properties XML element."""
        requirements_properties = etree.SubElement(parent_element, "properties")

        req_properties_conf = self.config.get("requirements_import_properties") or {}
        for name, value in sorted(req_properties_conf.items()):
            if name == "lookup-method":
                lookup_prop = str(value).lower()
                if lookup_prop not in ("id", "name"):
                    raise Dump2PolarionException(
                        "Invalid value '{}' for the 'lookup-method' property".format(str(value))
                    )
                self._lookup_prop = lookup_prop
            else:
                etree.SubElement(
                    requirements_properties, "property", {"name": name, "value": str(value)}
                )

        return requirements_properties

    def _fill_lookup_prop(self, requirements_properties: etree.Element) -> None:
        """Fill the polarion-lookup-method property."""
        if not self._lookup_prop:
            raise Dump2PolarionException("Failed to set the 'polarion-lookup-method' property")

        etree.SubElement(
            requirements_properties,
            "property",
            {"name": "lookup-method", "value": self._lookup_prop},
        )

    def _check_lookup_prop(self, req_id: Optional[str]) -> bool:
        """Check that selected lookup property can be used for this testcase."""
        if self._lookup_prop:
            if not req_id and self._lookup_prop == "id":
                return False
        else:
            if req_id:
                self._lookup_prop = "id"
            else:
                self._lookup_prop = "name"
        return True

    def _classify_data(self, req_data: dict) -> Tuple[dict, dict]:
        attrs, custom_fields = {}, {}

        for key, value in req_data.items():
            if not value:
                continue
            conv_key = key.replace("_", "-")  # convert pythonic key_param to polarion 'key-param'
            for key_variant in (conv_key, key):
                if key_variant in self.requirement_transform.REQ_DATA:
                    attrs[key_variant] = value
                elif key_variant in self.known_custom_fields:
                    custom_fields[key_variant] = value
                if conv_key == key:
                    break

        return attrs, custom_fields

    @staticmethod
    def _fill_custom_fields(parent: etree.Element, custom_fields: dict) -> None:
        if not custom_fields:
            return

        custom_fields_el = etree.SubElement(parent, "custom-fields")
        for field, content in custom_fields.items():
            etree.SubElement(
                custom_fields_el,
                "custom-field",
                utils.sorted_dict({"id": field, "content": content}),
            )

    def _requirement_element(self, parent_element: etree.Element, req_data: dict) -> None:
        """Add requirement XML element."""
        req_data = self.requirement_transform.transform(req_data)
        if not req_data:
            return

        title = req_data.get("title")

        req_id = req_data.get("id")
        if not self._check_lookup_prop(req_id):
            LOGGER.warning(
                "Skipping requirement `%s`, data missing for selected lookup method", title
            )
            return

        attrs, custom_fields = self._classify_data(req_data)

        # For testing purposes, the order of fields in resulting XML
        # needs to be always the same.
        attrs = utils.sorted_dict(attrs)
        custom_fields = utils.sorted_dict(custom_fields)

        requirement = etree.SubElement(parent_element, "requirement", attrs)

        title_el = etree.SubElement(requirement, "title")
        title_el.text = utils.get_unicode_str(title)

        description = req_data.get("description")
        if description:
            description_el = etree.SubElement(requirement, "description")
            description_el.text = utils.get_unicode_str(description)

        self._fill_custom_fields(requirement, custom_fields)

    def _fill_requirements(self, parent_element: etree.Element) -> None:
        if not self.requirements_data:
            raise NothingToDoException("Nothing to export")
        for req_data in self.requirements_data:
            self._requirement_element(parent_element, req_data)

    def export(self) -> str:
        """Return requirements XML."""
        top = self._top_element()
        properties = self._properties_element(top)
        self._fill_requirements(top)
        self._fill_lookup_prop(properties)
        return utils.prettify_xml(top)

    @staticmethod
    def write_xml(xml_str: str, output_file: Optional[str] = None) -> None:
        """Output the XML content into a file."""
        gen_filename = "requirements-{:%Y%m%d%H%M%S}.xml".format(datetime.datetime.now())
        utils.write_xml(xml_str, output_loc=output_file, filename=gen_filename)
