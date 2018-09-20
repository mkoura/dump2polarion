# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access

from __future__ import unicode_literals

import os

import pytest

from dump2polarion import jsontools
from dump2polarion.exceptions import Dump2PolarionException
from tests import conf

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class TestJSONImport(object):
    def test_import_orig_data(self):
        json_file = os.path.join(conf.DATA_PATH, "test_run_import.json")
        data = jsontools.import_json(json_file)
        assert hasattr(data, "results")
        assert len(data.results) == 18
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
        assert passed_num == 9
        assert failed_num == 4
        assert skipped_num == 3
        assert hasattr(data, "testrun")
        assert data.testrun is None

    def test_invalid_input(self):
        invalid_content = str("foo")
        input_file = StringIO(invalid_content)
        with pytest.raises(Dump2PolarionException) as excinfo:
            jsontools.import_json(input_file)
        input_file.close()
        assert "Cannot load results from" in str(excinfo.value)
