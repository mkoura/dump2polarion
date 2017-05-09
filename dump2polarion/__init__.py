# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Dump testcases results to xunit file and submit it to Polarion® xunit importer.
"""

from __future__ import print_function, unicode_literals

import csv
import os
import datetime
import logging
import re

from collections import OrderedDict, namedtuple

import sqlite3
from sqlite3 import Error

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

        for name, value in self.config['xunit_import_properties'].iteritems():
            SubElement(testsuites_properties, 'property',
                       {'name': name, 'value': str(value)})

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
        cflist = (os.path.expanduser('~/.config/dump2polarion.yaml'), 'dump2polarion.yaml')

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


def get_csv_fieldnames(csv_reader):
    """Finds fieldnames in Polarion exported csv file."""
    fieldnames = []
    for row in csv_reader:
        for col in row:
            field = (col.
                     strip().
                     replace('"', '').
                     replace(' ', '').
                     replace('(', '').
                     replace(')', '').
                     lower())
            fieldnames.append(field)
        if 'id' in fieldnames:
            break
        else:
            # this is not a row with fieldnames
            del fieldnames[:]
    if not fieldnames:
        return
    # remove trailing unannotated fields
    while True:
        field = fieldnames.pop()
        if field:
            fieldnames.append(field)
            break
    # name unannotated fields
    suffix = 1
    for index, field in enumerate(fieldnames):
        if not field:
            fieldnames[index] = 'field{}'.format(suffix)
            suffix += 1

    return fieldnames


def get_testrun_from_csv(csv_file, csv_reader):
    """Tries to find the testrun id in  Polarion exported csv file."""
    csv_file.seek(0)
    search_str = r'TEST_RECORDS:\("[^/]+/([^"]+)"'
    testrun_id = None
    too_far = False
    for row in csv_reader:
        for col in row:
            if not col:
                continue
            field = (col.
                     strip().
                     replace('"', '').
                     replace(' ', '').
                     replace('(', '').
                     replace(')', '').
                     lower())
            if field == 'id':
                # we are too far, tests results start here
                too_far = True
                break
            search = re.search(search_str, col)
            try:
                testrun_id = search.group(1)
            except AttributeError:
                continue
            else:
                break
        if testrun_id or too_far:
            break

    return testrun_id


def import_csv(csv_file):
    """Reads the content of the Polarion exported csv file and returns imported data."""
    with open(os.path.expanduser(csv_file), 'rb') as input_file:
        reader = csv.reader(input_file, delimiter=str(';'), quotechar=str('"'))

        fieldnames = get_csv_fieldnames(reader)
        if not fieldnames:
            raise Dump2PolarionException("Cannot find field names in CSV file {}".format(csv_file))
        fieldnames_len = len(fieldnames)

        # map data to fieldnames
        results = []
        for row in reader:
            record = OrderedDict(zip(fieldnames, row))
            # skip rows that were already exported
            if record.get('exported') == 'yes':
                continue
            row_len = len(row)
            if fieldnames_len > row_len:
                for key in fieldnames[row_len:]:
                    record[key] = None
            results.append(record)

        testrun = get_testrun_from_csv(input_file, reader)

    return ImportedData(results=results, testrun=testrun)


def get_testrun_from_sqlite(conn):
    """Returns testrun id saved from original csv file."""
    cur = conn.cursor()
    try:
        cur.execute('SELECT testrun FROM testrun')
        return cur.fetchone()[0]
    except (IndexError, Error):
        return


def import_sqlite(db_file):
    """Reads the content of the database file and returns imported data."""
    with open(db_file):
        # test that file can be accessed
        pass
    try:
        conn = sqlite3.connect(os.path.expanduser(db_file))
    except Error as err:
        raise Dump2PolarionException('{}'.format(err))

    cur = conn.cursor()
    # get all rows that were not exported yet
    cur.execute("SELECT * FROM testcases WHERE exported != 'yes'")
    fieldnames = [description[0] for description in cur.description]
    rows = cur.fetchall()

    # mark all rows with verdict as exported
    cur.execute(
        "UPDATE testcases SET exported = 'yes' WHERE verdict is not null and verdict != ''")

    # map data to fieldnames
    results = []
    for row in rows:
        record = OrderedDict(zip(fieldnames, row))
        results.append(record)

    testrun = get_testrun_from_sqlite(conn)

    conn.commit()
    conn.close()

    return ImportedData(results=results, testrun=testrun)


def export_csv(csv_file, results):
    """Writes testcases results into csv file."""
    with open(os.path.expanduser(csv_file), 'wb') as output_file:
        csvwriter = csv.writer(output_file, delimiter=str(';'),
                               quotechar=str('|'), quoting=csv.QUOTE_MINIMAL)

        csvwriter.writerow(results[0].keys())
        for result in results:
            csvwriter.writerow(result.values())


def submit_to_polarion(xml, config, **kwargs):
    """Submits results to Polarion."""
    login = kwargs.get('user') or config.get('username') or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get('password') or config.get('password') or os.environ.get("POLARION_PASSWORD")
    xunit_target = config.get('xunit_target')

    if not all([login, pwd]):
        logger.error("Failed to submit data to Polarion - missing credentials")
        return
    if not xunit_target:
        logger.error("Failed to submit data to Polarion - missing 'xunit_target'")
        return

    if os.path.isfile(xml):
        files = {'file': ('results.xml', open(xml, 'rb'))}
    else:
        files = {'file': ('results.xml', xml)}

    logger.info("Submitting data to {}".format(xunit_target))
    return requests.post(xunit_target, files=files, auth=(login, pwd), verify=False)
