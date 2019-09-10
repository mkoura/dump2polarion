# pylint: disable=missing-docstring,no-self-use

import os

from dump2polarion.svn_polarion import WorkItemCache
from tests import conf

REPO_DIR = os.path.join(conf.DATA_PATH, "polarion_repo")
WORKITEMS_NUM = 3


class TestWorkItemCache:
    def test_get_all_items(self):
        cache = WorkItemCache(REPO_DIR)
        counter = 0
        for item in cache.get_all_items():
            assert item.get("title")
            assert item.get("type") == "testcase"
            counter += 1
        assert counter == WORKITEMS_NUM
