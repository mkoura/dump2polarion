# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import os
from StringIO import StringIO

import pytest

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion import csvtools


DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class TestFileldNames(object):
    def test_fieldnames_exported(self):
        csv_file = os.path.join(DATA_PATH, 'workitems_ids.csv')
        with open(csv_file, 'rb') as input_file:
            reader = csvtools.get_csv_reader(input_file)
            fieldnames = csvtools.get_csv_fieldnames(reader)
        assert fieldnames == [
            'id',
            'title',
            'testcaseid',
            'caseimportance',
            'verdict',
            'comment',
            'stdout',
            'stderr',
            'exported',
            'time'
        ]

    def test_fieldnames_unanotated(self):
        csv_content = str(',,ID,Title,Test Case I D,Caseimportance')
        input_file = StringIO(csv_content)
        reader = csvtools.get_csv_reader(input_file)
        fieldnames = csvtools.get_csv_fieldnames(reader)
        input_file.close()
        assert fieldnames == [
            'field1',
            'field2',
            'id',
            'title',
            'testcaseid',
            'caseimportance'
        ]

    def test_fieldnames_trailing(self):
        csv_content = str('ID,Title,Test Case I D,Caseimportance,,,')
        input_file = StringIO(csv_content)
        reader = csvtools.get_csv_reader(input_file)
        fieldnames = csvtools.get_csv_fieldnames(reader)
        input_file.close()
        assert fieldnames == [
            'id',
            'title',
            'testcaseid',
            'caseimportance'
        ]


class TestTestrunId(object):
    def test_testrun_id_exported(self):
        csv_file = os.path.join(DATA_PATH, 'workitems_ids.csv')
        with open(csv_file, 'rb') as input_file:
            reader = csvtools.get_csv_reader(input_file)
            testrun_id = csvtools.get_testrun_from_csv(input_file, reader)
        assert testrun_id == '5_8_0_17'

    def test_testrun_id_line(self):
        csv_content = str('Query,"(assignee.id:$[user.id] AND NOT status:inactive AND '
                          '(TEST_RECORDS:(""RHCF3/5_8_0_17"", @null))) '
                          'AND project.id:RHCF3",,,,,,,')
        input_file = StringIO(csv_content)
        reader = csvtools.get_csv_reader(input_file)
        testrun_id = csvtools.get_testrun_from_csv(input_file, reader)
        assert testrun_id == '5_8_0_17'

    def test_testrun_id_far(self):
        csv_content = str("""
            ,ID,Title,Test Case I D,,,,
            ,(TEST_RECORDS:(""RHCF3/5_8_0_17"", @null)),,,,,""")
        input_file = StringIO(csv_content)
        reader = csvtools.get_csv_reader(input_file)
        testrun_id = csvtools.get_testrun_from_csv(input_file, reader)
        assert not testrun_id


class TestImport(object):
    def test_import_orig_data(self):
        csv_file = os.path.join(DATA_PATH, 'workitems_ids.csv')
        data = csvtools.import_csv(csv_file)
        assert hasattr(data, 'results')
        assert len(data.results) == 15
        assert 'id' in data.results[0]

    def test_import_no_results(self, tmpdir):
        csv_content = str('ID,Title,Test Case I D,Caseimportance,,,')
        csv_file = tmpdir.join('no_results.csv')
        csv_file.write(csv_content)
        csv_file_path = str(csv_file)
        with pytest.raises(Dump2PolarionException):
            csvtools.import_csv(csv_file_path)

    def test_import_and_check_verdict(self, tmpdir):
        csv_content = str("""
            ,ID,Title,Test Case I D,,,,
            ,RH123,,,,,,""")
        csv_file = tmpdir.join('invalid_fieldnames.csv')
        csv_file.write(csv_content)
        csv_file_path = str(csv_file)
        with pytest.raises(Dump2PolarionException):
            csvtools.import_csv_and_check(csv_file_path)
