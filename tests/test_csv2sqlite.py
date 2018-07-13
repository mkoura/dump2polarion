# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use

import io
import os

from mock import patch

from dump2polarion import csv2sqlite_cli, dbtools
from dump2polarion.xunit_exporter import XunitExport
from tests import conf


class TestCSV2sqliteCLI(object):
    def test_get_args(self):
        args = csv2sqlite_cli.get_args(["-i", "foo", "-o", "bar"])
        assert args.input_file == "foo"
        assert args.output_file == "bar"
        assert args.log_level is None

    def test_e2e_ok(self, config_prop, tmpdir):
        input_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
        db_file = os.path.join(str(tmpdir), "workitems_copy.sqlite3")
        args = ["-i", input_file, "-o", db_file]
        with patch("dump2polarion.csv2sqlite_cli.utils.init_log"):
            retval = csv2sqlite_cli.main(args)
        assert retval == 0

        records = dbtools.import_sqlite(db_file)
        exporter = XunitExport("5_8_0_17", records, config_prop)
        complete = exporter.export()
        fname = "complete_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding="utf-8") as input_xml:
            parsed = input_xml.read()
        assert complete == parsed

    def test_e2e_invalid_csv(self, captured_log):
        non_file = "nonexistent.csv"
        args = ["-i", non_file, "-o", non_file]
        retval = csv2sqlite_cli.main(args)
        assert retval == 1
        assert "No such file or directory" in captured_log.getvalue()

    def test_e2e_not_csv(self, captured_log):
        non_file = "nonexistent.txt"
        args = ["-i", non_file, "-o", non_file]
        retval = csv2sqlite_cli.main(args)
        assert retval == 1
        assert "is in CSV format" in captured_log.getvalue()
