"""Utils for dump2polarion."""

import datetime
import logging
import os
import random
import re
import string
from collections import OrderedDict

import requests
import urllib3
from lxml import etree
from polarion_tools_common import utils

from dump2polarion.exceptions import Dump2PolarionException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)

NO_BLANKS_PARSER = etree.XMLParser(remove_blank_text=True)
# from https://stackoverflow.com/a/25920392
VALID_XML_RE = re.compile("[^\u0020-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\U00010000-\U0010FFFF]+")


def get_unicode_str(obj):
    """Make sure obj is a valid XML unicode string."""
    return VALID_XML_RE.sub("", utils.get_unicode_str(obj))


def init_log(log_level):
    """Initialize logging."""
    log_level = log_level or "INFO"
    logging.basicConfig(
        format="%(name)s:%(levelname)s:%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def _get_filename(output_loc=None, filename=None):
    filename = filename or "output-{:%Y%m%d%H%M%S}-{}.xml".format(
        datetime.datetime.now(), "".join(random.sample(string.ascii_lowercase, 5))
    )
    if output_loc:
        filename_fin = os.path.expanduser(output_loc)
        if os.path.isdir(filename_fin):
            filename_fin = os.path.join(filename_fin, filename)
    else:
        filename_fin = filename

    return filename_fin


def write_xml(xml_str, output_loc=None, filename=None):
    """Output the XML content (string) into a file.

    If `output_loc` is supplied and it's a file (not directory), the output
    will be saved there and the `filename` is ignored.

    Args:
        xml_str: string with XML document
        output_loc: file or directory for saving the file
        filename: file name that will be used if `output_loc` is directory
            If it is needed and is not supplied, it will be generated

    """
    if not xml_str:
        raise Dump2PolarionException("No data to write.")
    filename_fin = _get_filename(output_loc=output_loc, filename=filename)

    with open(filename_fin, "w", encoding="utf-8") as xml_file:
        xml_file.write(get_unicode_str(xml_str))
    logger.info("Data written to '%s'", filename_fin)


def write_xml_root(xml_root, output_loc=None, filename=None):
    """Output the XML content (from XML element) into a file.

    If `output_loc` is supplied and it's a file (not directory), the output
    will be saved there and the `filename` is ignored.

    Args:
        xml_root: root element ot the XML document
        output_loc: file or directory for saving the file
        filename: file name that will be used if `output_loc` is directory
            If it is needed and is not supplied, it will be generated

    """
    if xml_root is None:
        raise Dump2PolarionException("No data to write.")
    filename_fin = _get_filename(output_loc=output_loc, filename=filename)

    et = etree.ElementTree(xml_root)
    et.write(filename_fin, xml_declaration=True, pretty_print=True, encoding="utf-8")
    logger.info("Data written to '%s'", filename_fin)


def get_xml_root(xml_file):
    """Return XML root."""
    try:
        xml_root = etree.parse(os.path.expanduser(xml_file), NO_BLANKS_PARSER).getroot()
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML file '{}': {}".format(xml_file, err))
    return xml_root


def get_xml_root_from_str(xml_str):
    """Return XML root from string."""
    try:
        xml_root = etree.fromstring(xml_str.encode("utf-8"), NO_BLANKS_PARSER)
    # pylint: disable=broad-except
    except Exception as err:
        raise Dump2PolarionException("Failed to parse XML string: {}".format(err))
    return xml_root


def etree_to_string(xml_root):
    """Return string representation of element tree."""
    return get_unicode_str(etree.tostring(xml_root, encoding="utf-8"))


def prettify_xml(xml_root):
    """Return pretty-printed string representation of element tree."""
    xml_string = etree.tostring(xml_root, encoding="utf-8", xml_declaration=True, pretty_print=True)
    return get_unicode_str(xml_string)


def get_session(credentials, config):
    """Get requests session."""
    session = requests.Session()
    session.verify = False
    auth_url = config.get("auth_url")

    if auth_url:
        cookie = session.post(
            auth_url,
            data={
                "j_username": credentials[0],
                "j_password": credentials[1],
                "submit": "Log In",
                "rememberme": "true",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not cookie:
            raise Dump2PolarionException("Cookie was not retrieved from {}.".format(auth_url))
    else:
        # TODO: can be removed once basic auth is discontinued on prod
        session.auth = credentials

    return session


def get_testrun_id_config(config):
    """Get testrun ID defined in config file."""
    config_testrun_id = config.get("xunit_import_properties") or {}
    return config_testrun_id.get("polarion-testrun-id")


def sorted_dict(dictionary):
    """Return sorted dictionary."""
    return OrderedDict(sorted(dictionary.items()))
