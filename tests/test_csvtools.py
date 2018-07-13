# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os

import pytest

from dump2polarion import csvtools
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class TestCSVFileldNames(object):
    def test_fieldnames_exported(self):
        csv_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
        open_args = []
        open_kwargs = {}
        try:
            # pylint: disable=pointless-statement
            unicode
            open_args.append("rb")
        except NameError:
            open_kwargs["encoding"] = "utf-8"
        with open(csv_file, *open_args, **open_kwargs) as input_file:
            reader = csvtools._get_csv_reader(input_file)
            fieldnames = csvtools._get_csv_fieldnames(reader)
        assert fieldnames == [
            "id",
            "title",
            "testcaseid",
            "caseimportance",
            "verdict",
            "comment",
            "stdout",
            "stderr",
            "exported",
            "time",
        ]

    def test_fieldnames_unanotated(self):
        csv_content = str(",,ID,Title,Test Case I D,Caseimportance")
        input_file = StringIO(csv_content)
        reader = csvtools._get_csv_reader(input_file)
        fieldnames = csvtools._get_csv_fieldnames(reader)
        input_file.close()
        assert fieldnames == ["field1", "field2", "id", "title", "testcaseid", "caseimportance"]

    def test_fieldnames_trailing(self):
        csv_content = str("ID,Title,Test Case I D,Caseimportance,,,")
        input_file = StringIO(csv_content)
        reader = csvtools._get_csv_reader(input_file)
        fieldnames = csvtools._get_csv_fieldnames(reader)
        input_file.close()
        assert fieldnames == ["id", "title", "testcaseid", "caseimportance"]

    def test_fieldnames_missing_id(self):
        csv_content = str("Title,Test Case I D,Caseimportance,,,")
        input_file = StringIO(csv_content)
        reader = csvtools._get_csv_reader(input_file)
        fieldnames = csvtools._get_csv_fieldnames(reader)
        input_file.close()
        assert fieldnames is None


class TestCSVTestrunId(object):
    def test_testrun_id_exported(self):
        csv_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
        open_args = []
        open_kwargs = {}
        try:
            # pylint: disable=pointless-statement
            unicode
            open_args.append("rb")
        except NameError:
            open_kwargs["encoding"] = "utf-8"
        with open(csv_file, *open_args, **open_kwargs) as input_file:
            reader = csvtools._get_csv_reader(input_file)
            testrun_id = csvtools._get_testrun_from_csv(input_file, reader)
        assert testrun_id == "5_8_0_17"

    def test_testrun_id_line(self):
        csv_content = str(
            'Query,"(assignee.id:$[user.id] AND NOT status:inactive AND '
            '(TEST_RECORDS:(""RHCF3/5_8_0_17"", @null))) '
            'AND project.id:RHCF3",,,,,,,'
        )
        input_file = StringIO(csv_content)
        reader = csvtools._get_csv_reader(input_file)
        testrun_id = csvtools._get_testrun_from_csv(input_file, reader)
        assert testrun_id == "5_8_0_17"

    def test_testrun_id_far(self):
        csv_content = str(
            """
            ,ID,Title,Test Case I D,,,,
            ,(TEST_RECORDS:(""RHCF3/5_8_0_17"", @null)),,,,,"""
        )
        input_file = StringIO(csv_content)
        reader = csvtools._get_csv_reader(input_file)
        testrun_id = csvtools._get_testrun_from_csv(input_file, reader)
        assert not testrun_id


class TestCSVImport(object):
    def test_import_orig_data(self):
        csv_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
        data = csvtools.get_imported_data(csv_file)
        assert hasattr(data, "results")
        assert len(data.results) == 15
        assert "id" in data.results[0]
        assert hasattr(data, "testrun")
        assert data.testrun == "5_8_0_17"

    def test_import_no_results(self, tmpdir):
        csv_content = str("ID,Title,Test Case I D,Caseimportance,,,")
        csv_file = tmpdir.join("no_results.csv")
        csv_file.write(csv_content)
        csv_file_path = str(csv_file)
        with pytest.raises(Dump2PolarionException) as excinfo:
            csvtools.get_imported_data(csv_file_path)
        assert "No results read from CSV file" in str(excinfo.value)

    def test_import_and_check_verdict(self, tmpdir):
        csv_content = str(
            """
            ,ID,Title,Test Case I D,,,,
            ,RH123,,,,,,"""
        )
        csv_file = tmpdir.join("invalid_fieldnames.csv")
        csv_file.write(csv_content)
        csv_file_path = str(csv_file)
        with pytest.raises(Dump2PolarionException) as excinfo:
            csvtools.import_csv(csv_file_path)
        assert "missing following columns: Verdict" in str(excinfo.value)
