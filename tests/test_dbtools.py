# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import datetime
import io
import os
import shutil

import pytest

from dump2polarion import dbtools
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.xunit_exporter import XunitExport
from tests import conf


@pytest.fixture(scope="module")
def records_db():
    db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
    return dbtools.import_sqlite(db_file)


class TestDB(object):
    def test_testrun_id_exported(self):
        db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
        conn = dbtools._open_sqlite(db_file)
        testrun_id = dbtools._get_testrun_from_sqlite(conn)
        assert testrun_id == "5_8_0_17"

    def test_testrun_invalid_db(self):
        db_file = os.path.join(conf.DATA_PATH, "ostriz.json")
        conn = dbtools._open_sqlite(db_file)
        testrun_id = dbtools._get_testrun_from_sqlite(conn)
        assert testrun_id is None

    def test_import_orig_data(self, records_db):
        assert hasattr(records_db, "results")
        assert len(records_db.results) == 15
        assert "id" in records_db.results[0]
        assert hasattr(records_db, "testrun")
        assert records_db.testrun == "5_8_0_17"

    def test_import_time(self):
        db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
        older_than = datetime.datetime(2017, 6, 15)
        records = dbtools.import_sqlite(db_file, older_than=older_than)
        assert hasattr(records, "results")
        assert len(records.results) == 14

    def test_open_nonexistent(self):
        db_file = "nonexistent"
        with pytest.raises(Dump2PolarionException) as excinfo:
            dbtools._open_sqlite(db_file)
        assert "No such file or directory" in str(excinfo.value)

    def test_exported_older_than(self, tmpdir):
        orig_db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
        older_than = datetime.datetime(2017, 6, 15)
        db_file = os.path.join(str(tmpdir), "workitems_copy.sqlite3")
        shutil.copy(orig_db_file, db_file)
        dbtools.mark_exported_sqlite(db_file, older_than=older_than)
        conn = dbtools._open_sqlite(db_file)
        cur = conn.cursor()
        select = "SELECT count(*) FROM testcases WHERE exported == 'yes'"
        cur.execute(select)
        num = cur.fetchone()
        conn.close()
        assert num[0] == 12

    def test_exported_all(self, tmpdir):
        orig_db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
        db_file = os.path.join(str(tmpdir), "workitems_copy.sqlite3")
        shutil.copy(orig_db_file, db_file)
        dbtools.mark_exported_sqlite(db_file)
        conn = dbtools._open_sqlite(db_file)
        cur = conn.cursor()
        select = "SELECT count(*) FROM testcases WHERE exported == 'yes'"
        cur.execute(select)
        num = cur.fetchone()
        conn.close()
        assert num[0] == 13

    def test_e2e_ids_notransform(self, config_prop, records_db):
        exporter = XunitExport("5_8_0_17", records_db, config_prop, transform_func=lambda arg: arg)
        complete = exporter.export()
        fname = "complete_notransform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_ids_transform(self, config_prop, records_db):
        exporter = XunitExport("5_8_0_17", records_db, config_prop)
        complete = exporter.export()
        fname = "complete_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed
