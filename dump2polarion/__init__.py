# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results to xunit file and submit it to the Polarion® XUnit Importer.
"""

from __future__ import unicode_literals

import os
import datetime
import string
import random
import logging

from collections import namedtuple

from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment

import yaml
import requests

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


ImportedData = namedtuple('ImportedData', 'results testrun')


class Dump2PolarionException(Exception):
    """dump2polarion exception."""


class XunitExport(object):
    """Exports testcases results into Polarion xunit."""
    PASS = ('passed', 'pass')
    FAIL = ('failed', 'fail')
    SKIP = ('skipped', 'skip', 'blocked')
    WAIT = ('null', 'wait', 'waiting')

    def __init__(self, testrun_id, tests_records, config, only_passed=False):
        self.testrun_id = testrun_id
        self.tests_records = tests_records
        self.config = config
        self.only_passed = only_passed

    def top_element(self):
        """Returns top XML element."""
        top = Element('testsuites')
        comment = Comment("Generated for testrun {}".format(self.testrun_id))
        top.append(comment)
        return top

    def properties_element(self, parent_element):
        """Returns properties XML element."""
        testsuites_properties = SubElement(parent_element, 'properties')

        SubElement(testsuites_properties, 'property',
                   {'name': 'polarion-testrun-id', 'value': str(self.testrun_id)})

        response_prop_set = False
        for name, value in self.config['xunit_import_properties'].iteritems():
            SubElement(testsuites_properties, 'property',
                       {'name': name, 'value': str(value)})
            if 'polarion-response-' in name:
                response_prop_set = True

        if not response_prop_set:
            name = 'polarion-response-dump2polarion'
            value = ''.join(random.sample(string.lowercase, 10))
            SubElement(testsuites_properties, 'property', {'name': name, 'value': value})

        return testsuites_properties

    def testsuite_element(self, parent_element):
        """Returns testsuite XML element."""
        testsuite = SubElement(
            parent_element,
            'testsuite',
            {'name': 'Import for {} - {} testrun'.format(
                self.config['xunit_import_properties']['polarion-project-id'], self.testrun_id)})
        return testsuite

    def gen_testcase(self, parent_element, result, records):
        """Creates XML element for given testcase result and update testcases records."""
        verdict = result.get('verdict', '').strip().lower()
        if not (result.get('id') and
                verdict in self.PASS + self.FAIL + self.SKIP + self.WAIT):
            return
        if self.only_passed and verdict not in self.PASS:
            return

        testcase_time = float(result.get('time') or result.get('duration') or 0)
        records['time'] += testcase_time

        testcase_data = {
            'classname': 'TestClass',
            'name': result.get('title') or result.get('id'),
            'time': str(testcase_time)}
        testcase = SubElement(parent_element, 'testcase', testcase_data)

        # xunit Pass maps to Passed in Polarion
        if verdict in self.PASS:
            records['passed'] += 1
        # xunit Failure maps to Failed in Polarion
        elif verdict in self.FAIL:
            records['failures'] += 1
            verdict_data = {'type': 'failure'}
            if result.get('comment'):
                verdict_data['message'] = str(result['comment'])
            SubElement(testcase, 'failure', verdict_data)
        # xunit Error maps to Blocked in Polarion
        elif verdict in self.SKIP:
            records['skipped'] += 1
            verdict_data = {'type': 'error'}
            if result.get('comment'):
                verdict_data['message'] = str(result['comment'])
            SubElement(testcase, 'error', verdict_data)
        # xunit Skipped maps to Waiting in Polarion
        elif verdict in self.WAIT:
            records['waiting'] += 1
            verdict_data = {'type': 'skipped'}
            if result.get('comment'):
                verdict_data['message'] = str(result['comment'])
            SubElement(testcase, 'skipped', verdict_data)

        if result.get('stdout'):
            system_out = SubElement(testcase, 'system-out')
            system_out.text = str(result['stdout'])

        if result.get('stderr'):
            system_err = SubElement(testcase, 'system-err')
            system_err.text = str(result['stderr'])

        properties = SubElement(testcase, 'properties')
        SubElement(properties, 'property',
                   {'name': 'polarion-testcase-id', 'value': result['id']})

    def fill_tests_results(self, testsuite_element):
        """Creates records for all testcases results."""
        records = dict(passed=0, skipped=0, failures=0, waiting=0, time=0.0)
        for testcase_result in self.tests_records.results:
            self.gen_testcase(testsuite_element, testcase_result, records)

        tests_num = (
            records['passed'] +
            records['skipped'] +
            records['failures'] +
            records['waiting'])

        testsuite_element.set('errors', str(records['skipped']))
        testsuite_element.set('failures', str(records['failures']))
        testsuite_element.set('skipped', str(records['waiting']))
        testsuite_element.set('time', str(records['time']))
        testsuite_element.set('tests', str(tests_num))

    @staticmethod
    def prettify(top_element):
        """Returns a pretty-printed XML."""
        rough_string = ElementTree.tostring(top_element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')

    def export(self):
        """Returns xunit XML."""
        top = self.top_element()
        self.properties_element(top)
        testsuite = self.testsuite_element(top)
        self.fill_tests_results(testsuite)
        return self.prettify(top)

    def write_xml(self, xml, output_file=None):
        """Outputs the XML content into a file."""
        gen_filename = 'testrun_{}-{:%Y%m%d%H%M%S}.xml'.format(
            self.testrun_id, datetime.datetime.now())
        if output_file:
            filename = os.path.expanduser(output_file)
            if os.path.isdir(filename):
                filename = os.path.join(filename, gen_filename)
        else:
            filename = gen_filename

        with open(filename, 'w') as xml_file:
            xml_file.write(xml)
        logger.info("Data written to '{}'".format(filename))


def get_config(config_file=None):
    """Finds and reads config file and returns its content."""
    if config_file:
        # config file specified
        cflist = (os.path.expanduser(config_file), )
    else:
        # find config file in default locations
        cflist = (
            os.path.expanduser('~/.config/dump2polarion.yaml'),
            'dump2polarion.yaml',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dump2polarion.yaml'))

    conf = None
    for cfile in cflist:
        try:
            with open(cfile):
                conf = cfile
                break
        except EnvironmentError:
            pass

    if not conf:
        if config_file:
            raise EnvironmentError("cannot open config file '{}'".format(config_file))
        else:
            raise EnvironmentError("no config file found")

    with open(conf, 'r') as input_file:
        config_settings = yaml.load(input_file)
    logger.info("Config loaded from '{}'".format(conf))

    return config_settings


def submit_to_polarion(xunit, config, **kwargs):
    """Submits results to Polarion."""
    login = kwargs.get('user') or config.get('username') or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get('password') or config.get('password') or os.environ.get("POLARION_PASSWORD")
    xunit_target = config.get('xunit_target')

    if not all([login, pwd]):
        logger.error("Failed to submit results to Polarion - missing credentials")
        return
    if not xunit_target:
        logger.error("Failed to submit results to Polarion - missing 'xunit_target'")
        return

    if os.path.isfile(xunit):
        files = {'file': ('results.xml', open(xunit, 'rb'))}
    else:
        files = {'file': ('results.xml', xunit)}

    logger.info("Submitting results to {}".format(xunit_target))
    try:
        response = requests.post(xunit_target, files=files, auth=(login, pwd), verify=False)
    # pylint: disable=broad-except
    except Exception as err:
        logger.error(err)
        response = None

    if response is None:
        logger.error("Failed to submit results to {}".format(xunit_target))
    elif response:
        logger.info("Results received by XUnit Importer (HTTP status {})".format(
            response.status_code))
    else:
        logger.error("HTTP status {}: failed to submit results to {}".format(
            response.status_code, xunit_target))

    return response
