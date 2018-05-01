# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Utils for dump2polarion.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import io
import logging
import os
import random
import string

from xml.etree import ElementTree

import requests

from dump2polarion.exceptions import Dump2PolarionException

# requests package backwards compatibility mess
# pylint: disable=import-error,ungrouped-imports,wrong-import-order
from requests.packages.urllib3.exceptions import InsecureRequestWarning as IRWrequests
# pylint: disable=no-member
requests.packages.urllib3.disable_warnings(IRWrequests)
try:
    import urllib3
    from urllib3.exceptions import InsecureRequestWarning as IRWurllib3
    urllib3.disable_warnings(IRWurllib3)
except ImportError:
    pass


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

_VERSION_ID = '23'
_NOT_EXPECTED_FORMAT_MSG = 'XML file is not in expected format'


def get_unicode_str(obj):
    """Makes sure obj is a unicode string."""
    try:
        # Python 2.x
        if isinstance(obj, unicode):
            return obj
        if isinstance(obj, str):
            return obj.decode('utf-8', errors='ignore')
        return unicode(obj)
    except NameError:
        # Python 3.x
        if isinstance(obj, str):
            return obj
        if isinstance(obj, bytes):
            return obj.decode('utf-8', errors='ignore')
        return str(obj)


def init_log(log_level):
    """Initializes logging."""
    log_level = log_level or 'INFO'
    logging.basicConfig(
        format='%(name)s:%(levelname)s:%(message)s',
        level=getattr(logging, log_level.upper(), logging.INFO))


def write_xml(xml, output_loc=None, filename=None):
    """Outputs the XML content into a file.

    Args:
        xml: string with XML document
        output_loc: file or directory for saving the file
        filename: file name that will be used if output_loc is directory
            If it is needed and is not supplied, it will be generated
    """
    if not xml:
        raise Dump2PolarionException("No data to write.")
    filename = filename or 'output-{}-{:%Y%m%d%H%M%S}.xml'.format(
        ''.join(random.sample(string.ascii_lowercase, 5)), datetime.datetime.now())
    if output_loc:
        filename_fin = os.path.expanduser(output_loc)
        if os.path.isdir(filename_fin):
            filename_fin = os.path.join(filename_fin, filename)
    else:
        filename_fin = filename

    with io.open(filename_fin, 'w', encoding='utf-8') as xml_file:
        xml_file.write(get_unicode_str(xml))
    logger.info("Data written to '{}'".format(filename_fin))


def get_xml_root(xml_file):
    """Returns XML root."""
    try:
        xml_tree = ElementTree.parse(os.path.expanduser(xml_file))
        xml_root = xml_tree.getroot()
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(xml_file, err))
    return xml_root


def get_xml_root_from_str(xml):
    """Returns XML root from string."""
    try:
        xml_root = ElementTree.fromstring(xml.encode('utf-8'))
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file: {}".format(err))
    return xml_root


def etree_to_string(xml_root):
    """Returns string representation of element tree."""
    return get_unicode_str(ElementTree.tostring(xml_root, encoding='utf-8'))


def xunit_fill_testrun_id(xml_root, testrun_id):
    """Adds the polarion-testrun-id property when it's missing."""
    if xml_root.tag == 'testcases':
        return
    if xml_root.tag != 'testsuites':
        raise Dump2PolarionException(
            "{} {}".format(_NOT_EXPECTED_FORMAT_MSG, "- missing <testsuites>"))
    properties = xml_root.find('properties')
    if properties is None:
        raise Dump2PolarionException("Failed to find <properties> in the XML file")
    for prop in properties:
        if prop.get('name') == 'polarion-testrun-id':
            break
    else:
        if not testrun_id:
            raise Dump2PolarionException(
                "Failed to submit results to Polarion - missing testrun id")
        ElementTree.SubElement(properties, 'property',
                               {'name': 'polarion-testrun-id', 'value': str(testrun_id)})


def generate_response_property(name=None, value=None):
    """Generates response property."""
    name = name or 'dump2polarion'
    value = value or ''.join(random.sample(string.ascii_lowercase, 9)) + _VERSION_ID
    return (name, value)


def _fill_testsuites_response_property(xml_root, name, value):
    """Returns testsuites response property and fills it if missing."""
    properties = xml_root.find('properties')
    for prop in properties:
        prop_name = prop.get('name', '')
        if 'polarion-response-' in prop_name:
            response_property = (prop_name[len('polarion-response-'):], str(prop.get('value')))
            break
    else:
        prop_name = 'polarion-response-{}'.format(name)
        ElementTree.SubElement(properties, 'property', {'name': prop_name, 'value': value})
        response_property = (name, value)

    return response_property


def _fill_testcases_response_property(xml_root, name, value):
    """Returns testcases response property and fills it if missing."""
    properties = xml_root.find('response-properties')
    if properties is None:
        properties = ElementTree.Element('response-properties')
        # response properties needs to be on top!
        xml_root.insert(0, properties)
    for prop in properties:
        if prop.tag == 'response-property':
            prop_name = prop.get('name')
            prop_value = prop.get('value')
            if prop_name and prop_value:
                response_property = (prop_name, str(prop_value))
            break
    else:
        ElementTree.SubElement(properties, 'response-property', {'name': name, 'value': value})
        response_property = (name, value)

    return response_property


def fill_response_property(xml_root, name=None, value=None):
    """Returns response property and fills it if missing."""
    name, value = generate_response_property(name, value)
    response_property = None

    if xml_root.tag == 'testsuites':
        response_property = _fill_testsuites_response_property(xml_root, name, value)
    elif xml_root.tag == 'testcases':
        response_property = _fill_testcases_response_property(xml_root, name, value)
    else:
        raise Dump2PolarionException(_NOT_EXPECTED_FORMAT_MSG)

    return response_property


def get_session(credentials, config):
    """Gets requests session."""
    session = requests.Session()
    session.verify = False
    auth_url = config.get('auth_url')

    if auth_url:
        cookie = session.post(
            auth_url,
            data={
                'j_username': credentials[0],
                'j_password': credentials[1],
                'submit': 'Log In',
                'rememberme': 'true'},
            headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if not cookie:
            raise Dump2PolarionException(
                'Cookie was not retrieved from {}.'.format(auth_url))
    else:
        # TODO: can be removed once basic auth is discontinued on prod
        session.auth = credentials

    return session
