# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results to xunit file for submitting to the Polarion XUnit Importer.
"""

from __future__ import unicode_literals, absolute_import

import datetime

from collections import namedtuple

from xml.dom import minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement, Comment

from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.verdicts import Verdicts
from dump2polarion.transform import get_results_transform
from dump2polarion.utils import write_xml, get_unicode_str


ImportedData = namedtuple('ImportedData', 'results testrun')


class XunitExport(object):
    """Exports testcases results into Polarion xunit."""
    def __init__(self, testrun_id, tests_records, config, transform_func=None):
        self.testrun_id = testrun_id
        self.tests_records = tests_records
        self.config = config
        self._lookup_prop = ''
        self._transform_func = transform_func or get_results_transform(config)

    def _top_element(self):
        """Returns top XML element."""
        top = Element('testsuites')
        comment = Comment("Generated for testrun {}".format(self.testrun_id))
        top.append(comment)
        return top

    def _properties_element(self, parent_element):
        """Returns properties XML element."""
        testsuites_properties = SubElement(parent_element, 'properties')

        SubElement(testsuites_properties, 'property',
                   {'name': 'polarion-testrun-id', 'value': str(self.testrun_id)})

        for name, value in sorted(self.config['xunit_import_properties'].items()):
            SubElement(testsuites_properties, 'property',
                       {'name': name, 'value': str(value)})
            if name == 'polarion-lookup-method':
                self._lookup_prop = str(value)

        if not self._lookup_prop:
            if 'id' in self.tests_records.results[0]:
                self._lookup_prop = 'ID'
            elif 'title' in self.tests_records.results[0]:
                self._lookup_prop = 'Name'
            else:
                raise Dump2PolarionException(
                    "Failed to set the 'polarion-lookup-method' property")
            SubElement(testsuites_properties, 'property',
                       {'name': 'polarion-lookup-method', 'value': self._lookup_prop})
        elif self._lookup_prop.lower() not in ('id', 'name', 'custom'):
            raise Dump2PolarionException(
                "Invalid value '{}' for the 'polarion-lookup-method' property".format(
                    self._lookup_prop))

        return testsuites_properties

    def _testsuite_element(self, parent_element):
        """Returns testsuite XML element."""
        testsuite = SubElement(
            parent_element,
            'testsuite',
            {'name': 'Import for {} - {} testrun'.format(
                self.config['xunit_import_properties']['polarion-project-id'], self.testrun_id)})
        return testsuite

    @staticmethod
    def _fill_verdict(verdict, result, testcase, records):
        # xunit Pass maps to Passed in Polarion
        if verdict in Verdicts.PASS:
            records['passed'] += 1
        # xunit Failure maps to Failed in Polarion
        elif verdict in Verdicts.FAIL:
            records['failures'] += 1
            verdict_data = {'type': 'failure'}
            if result.get('comment'):
                verdict_data['message'] = get_unicode_str(result['comment'])
            SubElement(testcase, 'failure', verdict_data)
        # xunit Error maps to Blocked in Polarion
        elif verdict in Verdicts.SKIP:
            records['skipped'] += 1
            verdict_data = {'type': 'error'}
            if result.get('comment'):
                verdict_data['message'] = get_unicode_str(result['comment'])
            SubElement(testcase, 'error', verdict_data)
        # xunit Skipped maps to Waiting in Polarion
        elif verdict in Verdicts.WAIT:
            records['waiting'] += 1
            verdict_data = {'type': 'skipped'}
            if result.get('comment'):
                verdict_data['message'] = get_unicode_str(result['comment'])
            SubElement(testcase, 'skipped', verdict_data)

    def _gen_testcase(self, parent_element, result, records):
        """Creates XML element for given testcase result and update testcases records."""
        if self._transform_func:
            result = self._transform_func(result)
            if not result:
                return
        verdict = result.get('verdict', '').strip().lower()
        if verdict not in Verdicts.PASS + Verdicts.FAIL + Verdicts.SKIP + Verdicts.WAIT:
            return
        testcase_id = result.get('id')
        testcase_title = result.get('title')
        if not testcase_id and self._lookup_prop.lower() == 'id':
            return
        if not testcase_title and self._lookup_prop.lower() == 'name':
            return

        testcase_time = float(result.get('time') or result.get('duration') or 0)
        records['time'] += testcase_time

        testcase_data = {
            'name': testcase_title or testcase_id,
            'time': str(testcase_time)}
        if result.get('classname'):
            testcase_data['classname'] = result['classname']
        testcase = SubElement(parent_element, 'testcase', testcase_data)

        self._fill_verdict(verdict, result, testcase, records)

        if result.get('stdout'):
            system_out = SubElement(testcase, 'system-out')
            system_out.text = get_unicode_str(result['stdout'])

        if result.get('stderr'):
            system_err = SubElement(testcase, 'system-err')
            system_err.text = get_unicode_str(result['stderr'])

        properties = SubElement(testcase, 'properties')
        SubElement(properties, 'property',
                   {'name': 'polarion-testcase-id', 'value': testcase_id or testcase_title})
        if verdict in Verdicts.PASS and result.get('comment'):
            SubElement(properties, 'property',
                       {'name': 'polarion-testcase-comment',
                        'value': get_unicode_str(result['comment'])})

    def _fill_tests_results(self, testsuite_element):
        """Creates records for all testcases results."""
        if not self.tests_records.results:
            raise NothingToDoException("Nothing to export")

        records = dict(passed=0, skipped=0, failures=0, waiting=0, time=0.0)
        for testcase_result in self.tests_records.results:
            self._gen_testcase(testsuite_element, testcase_result, records)

        tests_num = (
            records['passed'] +
            records['skipped'] +
            records['failures'] +
            records['waiting'])

        if tests_num == 0:
            raise NothingToDoException("Nothing to export")

        testsuite_element.set('errors', str(records['skipped']))
        testsuite_element.set('failures', str(records['failures']))
        testsuite_element.set('skipped', str(records['waiting']))
        testsuite_element.set('time', '{0:.4f}'.format(records['time']))
        testsuite_element.set('tests', str(tests_num))

    @staticmethod
    def _prettify(top_element):
        """Returns a pretty-printed XML."""
        rough_string = ElementTree.tostring(top_element, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return get_unicode_str(reparsed.toprettyxml(indent='  ', encoding='utf-8'))

    def export(self):
        """Returns xunit XML."""
        top = self._top_element()
        self._properties_element(top)
        testsuite = self._testsuite_element(top)
        self._fill_tests_results(testsuite)
        return self._prettify(top)

    def write_xml(self, xml, output_file=None):
        """Outputs the XML content into a file."""
        gen_filename = 'testrun_{}-{:%Y%m%d%H%M%S}.xml'.format(
            self.testrun_id, datetime.datetime.now())
        write_xml(xml, output_loc=output_file, filename=gen_filename)
