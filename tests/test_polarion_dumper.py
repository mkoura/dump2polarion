# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use

import io
import os
import shutil

import pytest
from mock import patch

from dump2polarion import dbtools, dumper_cli
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.transform import only_passed_and_wait
from tests import conf


class TestDumperCLIUnits(object):
    def test_get_args(self):
        args = dumper_cli.get_args(["-i", "dummy", "-t", "testrun_id"])
        assert args.input_file == "dummy"
        assert args.output_file is None
        assert args.testrun_id == "testrun_id"
        assert args.config_file is None
        assert args.no_submit is False
        assert args.user is None
        assert args.password is None
        assert args.force is False
        assert args.log_level is None

    def test_testrun_id_match(self):
        args = dumper_cli.get_args(["-i", "dummy", "-t", "5_8_0_17"])
        found = dumper_cli.get_testrun_id(args, "5_8_0_17")
        assert found == "5_8_0_17"

    def test_testrun_id_nomatch(self):
        args = dumper_cli.get_args(["-i", "dummy", "-t", "5_8_0_17"])
        with pytest.raises(Dump2PolarionException) as excinfo:
            dumper_cli.get_testrun_id(args, "5_8_0_18")
        assert "found in exported data doesn't match" in str(excinfo.value)

    def test_testrun_id_force(self):
        args = dumper_cli.get_args(["-i", "dummy", "-t", "5_8_0_18", "--force"])
        found = dumper_cli.get_testrun_id(args, "5_8_0_17")
        assert found == "5_8_0_18"

    def test_testrun_id_missing(self):
        args = dumper_cli.get_args(["-i", "dummy"])
        with pytest.raises(Dump2PolarionException) as excinfo:
            dumper_cli.get_testrun_id(args, None)
        assert "The testrun id was not specified" in str(excinfo.value)

    def test_submit_if_ready_noxml(self, config_prop):
        args = dumper_cli.get_args(["-i", "submit.txt"])
        submit_args = dumper_cli.get_submit_args(args)
        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.submit_if_ready(args, submit_args, config_prop)
        assert retval is None

    def test_submit_if_ready_nosubmit(self, tmpdir, config_prop):
        xml_content = "<testcases foo=bar>"
        xml_file = tmpdir.join("submit_nosubmit.xml")
        xml_file.write(xml_content)
        args = dumper_cli.get_args(["-i", str(xml_file), "--no-submit"])
        submit_args = dumper_cli.get_submit_args(args)
        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.submit_if_ready(args, submit_args, config_prop)
        assert retval == 0

    def test_submit_if_ready_failed(self, tmpdir, config_prop):
        xml_content = "<testcases foo=bar>"
        xml_file = tmpdir.join("submit_failed.xml")
        xml_file.write(xml_content)
        args = dumper_cli.get_args(["-i", str(xml_file)])
        submit_args = dumper_cli.get_submit_args(args)
        with patch("dump2polarion.submit_and_verify", return_value=False):
            retval = dumper_cli.submit_if_ready(args, submit_args, config_prop)
        assert retval == 2

    @pytest.mark.parametrize("tag", ("testsuites", "testcases"))
    def test_submit_if_ready_ok(self, tmpdir, config_prop, tag):
        xml_content = "<{} foo=bar>".format(tag)
        xml_file = tmpdir.join("submit_ready.xml")
        xml_file.write(xml_content)
        args = dumper_cli.get_args(["-i", str(xml_file)])
        submit_args = dumper_cli.get_submit_args(args)
        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.submit_if_ready(args, submit_args, config_prop)
        assert retval == 0


E2E_DATA = [
    # default transform
    ("junit-report.xml", "junit_transform.xml", ["-t", "5_8_0_17"], None),
    ("workitems_ids.csv", "complete_transform.xml", [], None),
    ("workitems_ids.sqlite3", "complete_transform.xml", [], None),
    ("ostriz.json", "ostriz_transform.xml", [], None),
    # no transform
    ("junit-report.xml", "junit_notransform.xml", ["-t", "5_8_0_17"], lambda arg: arg),
    ("workitems_ids.csv", "complete_notransform.xml", [], lambda arg: arg),
    ("workitems_ids.sqlite3", "complete_notransform.xml", [], lambda arg: arg),
    ("ostriz.json", "ostriz_notransform.xml", [], lambda arg: arg),
    # only passed and wait
    (
        "junit-report.xml",
        "junit_passed_wait_transform.xml",
        ["-t", "5_8_0_17"],
        only_passed_and_wait,
    ),
    ("workitems_ids.csv", "complete_passed_wait_transform.xml", [], only_passed_and_wait),
    ("workitems_ids.sqlite3", "complete_passed_wait_transform.xml", [], only_passed_and_wait),
    ("ostriz.json", "ostriz_passed_wait_transform.xml", [], only_passed_and_wait),
]


class TestDumperCLIE2E(object):
    @pytest.mark.parametrize("data", E2E_DATA, ids=[d[0] for d in E2E_DATA])
    @pytest.mark.parametrize("submit", (True, False), ids=("submit", "nosubmit"))
    # pylint: disable=too-many-locals
    def test_main_formats(self, tmpdir, config_e2e, data, submit):
        input_name, golden_output, extra_args, transform_func = data
        # copy the sqlite db so the records are not marked as exported
        if "sqlite3" in input_name:
            orig_db_file = os.path.join(conf.DATA_PATH, input_name)
            db_file = os.path.join(str(tmpdir), "workitems_copy.sqlite3")
            shutil.copy(orig_db_file, db_file)
            input_file = db_file
        else:
            input_file = os.path.join(conf.DATA_PATH, input_name)
        output_file = tmpdir.join("out.xml")
        args = ["-i", input_file, "-o", str(output_file), "-c", config_e2e]
        args.extend(extra_args)
        if not submit:
            args.append("-n")

        with patch("dump2polarion.submit_and_verify", return_value=True), patch(
            "dump2polarion.dumper_cli.utils.init_log"
        ):
            retval = dumper_cli.main(args, transform_func=transform_func)
        assert retval == 0

        with io.open(os.path.join(conf.DATA_PATH, golden_output), encoding="utf-8") as golden_xml:
            parsed = golden_xml.read()
        with io.open(str(output_file), encoding="utf-8") as out_xml:
            produced = out_xml.read()
        assert produced == parsed

    def test_main_missing_testrun(self, tmpdir, config_e2e, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "junit-report.xml")
        output_file = tmpdir.join("out.xml")
        args = ["-i", input_file, "-o", str(output_file), "-c", config_e2e, "-n"]

        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.main(args)
        assert retval == 1
        assert "The testrun id was not specified" in captured_log.getvalue()

        with pytest.raises(IOError) as excinfo:
            open(str(output_file))
        assert "No such file or directory" in str(excinfo.value)

    def test_main_submit_ready(self, config_e2e):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        args = ["-i", input_file, "-c", config_e2e]

        with patch("dump2polarion.submit_and_verify", return_value=True), patch(
            "dump2polarion.dumper_cli.utils.init_log"
        ):
            retval = dumper_cli.main(args)
        assert retval == 0

    def test_main_noreport(self, config_e2e):
        input_file = os.path.join(conf.DATA_PATH, "noreport.csv")
        args = ["-i", input_file, "-c", config_e2e]

        with patch("dump2polarion.submit_and_verify", return_value=True), patch(
            "dump2polarion.dumper_cli.utils.init_log"
        ):
            retval = dumper_cli.main(args)
        assert retval == 0

    def test_main_noresults(self, config_e2e, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "noresults.csv")
        args = ["-i", input_file, "-c", config_e2e]

        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.main(args)
        assert retval == 1
        assert "No results read from" in captured_log.getvalue()

    def test_main_unconfigured(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "noreport.csv")
        args = ["-i", input_file]

        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.main(args)
        assert retval == 1
        assert "Failed to find following keys in config file" in captured_log.getvalue()

    def test_main_noconfig(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "noreport.csv")
        args = ["-i", input_file, "-c", "nonexistent"]

        with patch("dump2polarion.submit_and_verify", return_value=True):
            retval = dumper_cli.main(args)
        assert retval == 1
        assert "Cannot open config file" in captured_log.getvalue()

    def test_main_submit_failed(self, tmpdir, config_e2e):
        input_file = os.path.join(conf.DATA_PATH, "workitems_ids.csv")
        output_file = tmpdir.join("out.xml")
        args = ["-i", input_file, "-o", str(output_file), "-c", config_e2e]

        with patch("dump2polarion.submit_and_verify", return_value=False), patch(
            "dump2polarion.dumper_cli.utils.init_log"
        ):
            retval = dumper_cli.main(args)
        assert retval == 2

        golden_output = "complete_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, golden_output), encoding="utf-8") as golden_xml:
            parsed = golden_xml.read()
        with io.open(str(output_file), encoding="utf-8") as out_xml:
            produced = out_xml.read()
        assert produced == parsed

    # pylint: disable=too-many-locals,protected-access
    def test_main_submit_db(self, tmpdir, config_e2e):
        orig_db_file = os.path.join(conf.DATA_PATH, "workitems_ids.sqlite3")
        db_file = os.path.join(str(tmpdir), "workitems_copy.sqlite3")
        shutil.copy(orig_db_file, db_file)

        output_file = tmpdir.join("out.xml")
        args = ["-i", db_file, "-o", str(output_file), "-c", config_e2e]

        with patch("dump2polarion.submit_and_verify", return_value=True), patch(
            "dump2polarion.dumper_cli.utils.init_log"
        ):
            retval = dumper_cli.main(args)
        assert retval == 0

        golden_output = "complete_transform.xml"
        with io.open(os.path.join(conf.DATA_PATH, golden_output), encoding="utf-8") as golden_xml:
            parsed = golden_xml.read()
        with io.open(str(output_file), encoding="utf-8") as out_xml:
            produced = out_xml.read()
        assert produced == parsed

        conn = dbtools._open_sqlite(db_file)
        cur = conn.cursor()
        select = "SELECT count(*) FROM testcases WHERE exported == 'yes'"
        cur.execute(select)
        num = cur.fetchone()
        conn.close()
        assert num[0] == 13
