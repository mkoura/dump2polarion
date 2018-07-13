# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import pytest

from dump2polarion.csvtools import import_csv
from dump2polarion.dbtools import SQLITE_EXT, import_sqlite
from dump2polarion.exceptions import Dump2PolarionException
from dump2polarion.importer import _get_importer
from dump2polarion.junittools import import_junit
from dump2polarion.ostriztools import import_ostriz


class TestImporterFormats(object):
    def test_ostriz_local(self):
        importer = _get_importer("test_ostriz_file.json")
        assert importer == import_ostriz

    def test_ostriz_remote(self):
        importer = _get_importer(
            "http://trackerbot/ostriz/jenkins/jenkins/downstream-58z-extcloud-tests-master"
        )
        assert importer == import_ostriz

    def test_junit(self):
        importer = _get_importer("test_junit.xml")
        assert importer == import_junit

    def test_csv(self):
        importer = _get_importer("workitems.csv")
        assert importer == import_csv

    @pytest.mark.parametrize("ext", SQLITE_EXT)
    def test_db(self, ext):
        importer = _get_importer("workitems{}".format(ext))
        assert importer == import_sqlite

    def test_invalid(self):
        with pytest.raises(Dump2PolarionException) as excinfo:
            _get_importer("workitems.txt")
        assert "Cannot recognize type of input data, add file extension" in str(excinfo.value)
