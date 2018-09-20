# -*- coding: utf-8 -*-
"""
Creates a Requirement XML file for submitting to the Polarion Importer.

Example of input requirements_data:
requirements_data = [
    {
        "title": "requirement_complete",
        "description": "Complete Requirement",
        "approver-ids": "mkourim:approved",
        "assignee-id": "mkourim",
        "category-ids": "category_id1, category_id2",
        "due-date": "2018-09-30",
        "planned-in-ids": "planned_id1, planned_id2",
        "initial-estimate": "1/4h",
        "priority-id": "high",
        "severity-id": "should_have",
        "status-id": "status_id",
        "reqtype": "functional",
    },
    {
        "title": "requirement_minimal",
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


class RequirementExport(object):
    """Exports requirements data into XML representation."""

    REQ_DATA = OrderedDict(
        (
            ("approver-ids", None),
            ("assignee-id", None),
            ("category-ids", None),
            ("due-date", None),
            ("initial-estimate", None),
            ("planned-in-ids", None),
            ("priority-id", "high"),
            ("severity-id", "should_have"),
            ("status-id", None),
        )
    )
    CUSTOM_FIELDS = OrderedDict((("reqtype", "functional"),))

    def __init__(self, requirements_data, config, transform_func=None):
        self.requirements_data = requirements_data
        self.config = config
        self._lookup_prop = ""
        self._transform_func = transform_func or transform.get_requirements_transform(config)

    def _transform_result(self, result):
        """Calls transform function on result."""
        if self._transform_func:
            result = self._transform_func(result)
        return result or None

    def _top_element(self):
        """Returns top XML element."""
        attrs = {"project-id": self.config["polarion-project-id"]}
        document_relative_path = self.config.get("requirements-document-relative-path")
        if document_relative_path:
            attrs["document-relative-path"] = document_relative_path
        top = etree.Element("requirements", attrs)
        return top

    def _properties_element(self, parent_element):
        """Returns properties XML element."""
        requirements_properties = etree.SubElement(parent_element, "properties")

        req_properties_conf = self.config.get("requirements_import_properties") or {}
        for name, value in sorted(six.iteritems(req_properties_conf)):
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

    def _fill_lookup_prop(self, requirements_properties):
        """Fills the polarion-lookup-method property."""
        if not self._lookup_prop:
            raise Dump2PolarionException("Failed to set the 'polarion-lookup-method' property")

        etree.SubElement(
            requirements_properties,
            "property",
            {"name": "lookup-method", "value": self._lookup_prop},
        )

    def _check_lookup_prop(self, req_id):
        """Checks that selected lookup property can be used for this testcase."""
        if self._lookup_prop:
            if not req_id and self._lookup_prop == "id":
                return False
        else:
            if req_id:
                self._lookup_prop = "id"
            else:
                self._lookup_prop = "name"
        return True

    def _classify_data(self, req_data):
        attrs = OrderedDict()
        custom_fields = OrderedDict()

        for key, value in six.iteritems(req_data):
            if not value:
                continue
            if key in self.REQ_DATA:
                attrs[key] = value
            elif key in self.CUSTOM_FIELDS:
                custom_fields[key] = value

        return attrs, custom_fields

    def _fill_defaults(self, attrs, custom_fields):
        for key, value in six.iteritems(self.REQ_DATA):
            if value and not attrs.get(key):
                attrs[key] = value
        for key, value in six.iteritems(self.CUSTOM_FIELDS):
            if value and not custom_fields.get(key):
                custom_fields[key] = value
        return attrs, custom_fields

    @staticmethod
    def _fill_custom_fields(parent, custom_fields):
        if not custom_fields:
            return

        custom_fields_el = etree.SubElement(parent, "custom-fields")
        for field, content in six.iteritems(custom_fields):
            etree.SubElement(custom_fields_el, "custom-field", {"id": field, "content": content})

    def _requirement_element(self, parent_element, req_data):
        """Adds requirement XML element."""
        req_data = self._transform_result(req_data)
        if not req_data:
            return

        title = req_data.get("title")
        if not title:
            return
        req_id = req_data.get("id")

        if not self._check_lookup_prop(req_id):
            return

        attrs, custom_fields = self._classify_data(req_data)
        attrs, custom_fields = self._fill_defaults(attrs, custom_fields)

        requirement = etree.SubElement(parent_element, "requirement", attrs)

        title_el = etree.SubElement(requirement, "title")
        title_el.text = title

        description = req_data.get("description")
        if description:
            description_el = etree.SubElement(requirement, "description")
            description_el.text = description

        self._fill_custom_fields(requirement, custom_fields)

    def _fill_requirements(self, parent_element):
        if not self.requirements_data:
            raise NothingToDoException("Nothing to export")
        for req_data in self.requirements_data:
            self._requirement_element(parent_element, req_data)

    def export(self):
        """Returns requirements XML."""
        top = self._top_element()
        properties = self._properties_element(top)
        self._fill_requirements(top)
        self._fill_lookup_prop(properties)
        return utils.prettify_xml(top)

    @staticmethod
    def write_xml(xml, output_file=None):
        """Outputs the XML content into a file."""
        gen_filename = "requirements-{:%Y%m%d%H%M%S}.xml".format(datetime.datetime.now())
        utils.write_xml(xml, output_loc=output_file, filename=gen_filename)
