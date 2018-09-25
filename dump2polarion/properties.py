# -*- coding: utf-8 -*-
"""
Tools for manipulation of XML properties.
"""

from __future__ import absolute_import, unicode_literals

import random
import string

from lxml import etree

from dump2polarion.exceptions import Dump2PolarionException

_NOT_EXPECTED_FORMAT_MSG = "XML file is not in expected format"


def xunit_fill_testrun_id(xml_root, testrun_id):
    """Adds the polarion-testrun-id property when it's missing."""
    if xml_root.tag in ("testcases", "requirements"):
        return
    if xml_root.tag != "testsuites":
        raise Dump2PolarionException(
            "{} {}".format(_NOT_EXPECTED_FORMAT_MSG, "- missing <testsuites>")
        )
    properties = xml_root.find("properties")
    if properties is None:
        raise Dump2PolarionException("Failed to find <properties> in the XML file")
    for prop in properties:
        if prop.get("name") == "polarion-testrun-id":
            break
    else:
        if not testrun_id:
            raise Dump2PolarionException(
                "Failed to submit results to Polarion - missing testrun id"
            )
        etree.SubElement(
            properties, "property", {"name": "polarion-testrun-id", "value": str(testrun_id)}
        )


def generate_response_property(name=None, value=None):
    """Generates response property."""
    name = name or "dump2polarion"
    value = value or "".join(random.sample(string.ascii_lowercase, 12))
    return (name, value)


def _fill_testsuites_response_property(xml_root, name, value):
    """Returns testsuites response property and fills it if missing."""
    properties = xml_root.find("properties")
    for prop in properties:
        prop_name = prop.get("name", "")
        if "polarion-response-" in prop_name:
            offset = len("polarion-response-")
            response_property = (prop_name[offset:], str(prop.get("value")))
            break
    else:
        prop_name = "polarion-response-{}".format(name)
        etree.SubElement(properties, "property", {"name": prop_name, "value": value})
        response_property = (name, value)

    return response_property


def _fill_non_testsuites_response_property(xml_root, name, value):
    """Returns testcases/requirements response property and fills it if missing."""
    properties = xml_root.find("response-properties")
    if properties is None:
        properties = etree.Element("response-properties")
        # response properties needs to be on top!
        xml_root.insert(0, properties)
    for prop in properties:
        if prop.tag == "response-property":
            prop_name = prop.get("name")
            prop_value = prop.get("value")
            if prop_name and prop_value:
                response_property = (prop_name, str(prop_value))
            break
    else:
        etree.SubElement(properties, "response-property", {"name": name, "value": value})
        response_property = (name, value)

    return response_property


def fill_response_property(xml_root, name=None, value=None):
    """Returns response property and fills it if missing."""
    name, value = generate_response_property(name, value)
    response_property = None

    if xml_root.tag == "testsuites":
        response_property = _fill_testsuites_response_property(xml_root, name, value)
    elif xml_root.tag in ("testcases", "requirements"):
        response_property = _fill_non_testsuites_response_property(xml_root, name, value)
    else:
        raise Dump2PolarionException(_NOT_EXPECTED_FORMAT_MSG)

    return response_property


def remove_response_property(xml_root):
    """Removes response properties if exist."""
    if xml_root.tag == "testsuites":
        properties = xml_root.find("properties")
        resp_properties = []
        for prop in properties:
            prop_name = prop.get("name", "")
            if "polarion-response-" in prop_name:
                resp_properties.append(prop)
        for resp_property in resp_properties:
            properties.remove(resp_property)
    elif xml_root.tag in ("testcases", "requirements"):
        resp_properties = xml_root.find("response-properties")
        if resp_properties is not None:
            xml_root.remove(resp_properties)
    else:
        raise Dump2PolarionException(_NOT_EXPECTED_FORMAT_MSG)


def _set_property(xml_root, name, value):
    """Sets property to specified value."""
    properties = xml_root.find("properties")
    for prop in properties:
        if prop.get("name") == name:
            prop.set("value", value)
            break
    else:
        etree.SubElement(properties, "property", {"name": name, "value": value})


def set_lookup_method(xml_root, value):
    """Changes lookup method."""
    if xml_root.tag == "testsuites":
        _set_property(xml_root, "polarion-lookup-method", value)
    elif xml_root.tag in ("testcases", "requirements"):
        _set_property(xml_root, "lookup-method", value)
    else:
        raise Dump2PolarionException(_NOT_EXPECTED_FORMAT_MSG)


def set_dry_run(xml_root, value=False):
    """Sets dry-run so records are not updated, only log file is produced."""
    value_str = str(value).lower()
    assert value_str in ("true", "false")
    if xml_root.tag == "testsuites":
        _set_property(xml_root, "polarion-dry-run", value_str)
    elif xml_root.tag in ("testcases", "requirements"):
        _set_property(xml_root, "dry-run", value_str)
    else:
        raise Dump2PolarionException(_NOT_EXPECTED_FORMAT_MSG)
