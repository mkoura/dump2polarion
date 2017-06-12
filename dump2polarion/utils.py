# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Utils for dump2polarion.
"""

from __future__ import unicode_literals, absolute_import

import os
import datetime
import string
import random
import logging

from xml.etree import ElementTree

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
        ''.join(random.sample(string.lowercase, 5)), datetime.datetime.now())
    if output_loc:
        filename_fin = os.path.expanduser(output_loc)
        if os.path.isdir(filename_fin):
            filename_fin = os.path.join(filename_fin, filename)
    else:
        filename_fin = filename

    with open(filename_fin, 'w') as xml_file:
        xml_file.write(xml)
    logger.info("Data written to '{}'".format(filename_fin))


def xunit_fill_testrun_id(xml, testrun_id=None):
    """Adds the polarion-testrun-id property when it's missing."""
    try:
        xml_root = ElementTree.fromstring(xml)
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file: {}".format(err))

    properties = xml_root.find('properties')
    for prop in properties:
        if prop.get('name') == 'polarion-testrun-id':
            return xml

    if testrun_id:
        ElementTree.SubElement(properties, 'property',
                               {'name': 'polarion-testrun-id', 'value': str(testrun_id)})
        return ElementTree.tostring(xml_root, encoding='utf8')
    else:
        raise Dump2PolarionException(
            "The testrun id was not specified and not found in the input data.")