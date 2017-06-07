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

from dump2polarion.exceptions import Dump2PolarionException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def write_xml(xml, output_file=None, gen_filename=None):
    """Outputs the XML content into a file."""
    if not xml:
        raise Dump2PolarionException("No data to write.")
    gen_filename = gen_filename or 'output-{}-{:%Y%m%d%H%M%S}.xml'.format(
        ''.join(random.sample(string.lowercase, 5)), datetime.datetime.now())
    if output_file:
        filename = os.path.expanduser(output_file)
        if os.path.isdir(filename):
            filename = os.path.join(filename, gen_filename)
    else:
        filename = gen_filename

    with open(filename, 'w') as xml_file:
        xml_file.write(xml)
    logger.info("Data written to '{}'".format(filename))
