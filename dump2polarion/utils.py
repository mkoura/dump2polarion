# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Utils for dump2polarion.
"""

from __future__ import unicode_literals, absolute_import

import os
import io
import datetime
import string
import random
import logging

from xml.etree import ElementTree
from xml.etree.ElementTree import SubElement

from dump2polarion.exceptions import Dump2PolarionException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


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


def xunit_fill_testrun_id(xml, testrun_id):
    """Adds the polarion-testrun-id property when it's missing."""
    try:
        xml_root = ElementTree.fromstring(xml.encode('utf-8'))
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file: {}".format(err))

    properties = xml_root.find('properties')
    if properties is None:
        raise Dump2PolarionException("Failed to find <properties> in the XML file")
    for prop in properties:
        if prop.get('name') == 'polarion-testrun-id':
            return xml

    ElementTree.SubElement(properties, 'property',
                           {'name': 'polarion-testrun-id', 'value': str(testrun_id)})
    return get_unicode_str(ElementTree.tostring(xml_root, encoding='utf-8'))


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


def fill_response_property(xml, name=None, value=None):
    """Fills response property if missing."""
    try:
        xml_root = ElementTree.fromstring(xml.encode('utf-8'))
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file: {}".format(err))

    name = name or 'dump2polarion'
    value = value or ''.join(random.sample(string.ascii_lowercase, 9)) + '13'

    if xml_root.tag == 'testsuites':
        properties = xml_root.find('properties')
        for prop in properties:
            prop_name = prop.get('name', '')
            if 'polarion-response-' in prop_name:
                return xml
        name = 'polarion-response-{}'.format(name)
        SubElement(properties, 'property', {'name': name, 'value': value})
    elif xml_root.tag == 'testcases':
        properties = xml_root.find('response-properties')
        if properties is None:
            properties = SubElement(xml_root, 'response-properties')
        for prop in properties:
            if prop.tag == 'response-property':
                return xml
        SubElement(properties, 'response-property', {'name': name, 'value': value})

    return get_unicode_str(ElementTree.tostring(xml_root, encoding='utf-8'))
