# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

import os
from io import StringIO

import pytest

from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.results import junittools
from tests import conf


class TestJunitImport:
    def test_import_orig_data(self):
        junit_file = os.path.join(conf.DATA_PATH, "junit-report.xml")
        data = junittools.import_junit(junit_file)
        assert hasattr(data, "results")
        assert len(data.results) == 7
        passed_num = failed_num = skipped_num = 0
        for result in data.results:
            if result["verdict"] == "passed":
                passed_num += 1
            elif result["verdict"] == "failed":
                assert result["comment"]
                failed_num += 1
            elif result["verdict"] == "skipped":
                assert result["comment"]
                skipped_num += 1
        assert passed_num == 2
        assert failed_num == 2
        assert skipped_num == 3
        assert hasattr(data, "testrun")
        assert data.testrun is None

    def test_invalid_input(self):
        invalid_content = "foo"
        input_file = StringIO(invalid_content)
        with pytest.raises(Dump2PolarionException) as excinfo:
            junittools.import_junit(input_file)
        input_file.close()
        assert "Failed to parse XML file" in str(excinfo.value)

    def test_import_with_params(self):
        junit_file = os.path.join(conf.DATA_PATH, "junit-report-params.xml")
        data = junittools.import_junit(junit_file)
        assert hasattr(data, "results")
        assert len(data.results) == 2
        assert list(data.results[0]["params"].keys()) == ["pkg"]
        assert list(data.results[1]["params"].keys()) == ["api_ver", "package"]
        assert data.results[0]["id"] == "foobar"
        assert data.results[1]["id"] == "barbaz"
