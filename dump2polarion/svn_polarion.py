# -*- coding: utf-8 -*-
"""
Access work items data in the Polarion SVN repository.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os
from collections import defaultdict

from lxml import etree

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class InvalidObject(object):
    """Item not present."""

    pass


class WorkItemCache(object):
    """Cache of Polarion workitems."""

    def __init__(self, repo_dir):
        self.repo_dir = repo_dir
        self.test_case_dir = os.path.join(self.repo_dir, "tracker", "workitems")
        self._cache = defaultdict(dict)

    @staticmethod
    def get_path(num):
        """Gets a path from the workitem number.

        For example: 31942 will return 30000-39999/31000-31999/31900-31999
        """
        num = int(num)
        dig_len = len(str(num))
        paths = []
        for i in range(dig_len - 2):
            divisor = 10 ** (dig_len - i - 1)
            paths.append(
                "{}-{}".format((num // divisor) * divisor, (((num // divisor) + 1) * divisor) - 1)
            )
        return "/".join(paths)

    def get_tree(self, work_item_id):
        """Gets XML tree of the workitem."""
        try:
            __, tcid = work_item_id.split("-")
        except ValueError:
            logger.warning("Couldn't load workitem %s, bad format", work_item_id)
            self._cache[work_item_id] = InvalidObject()
            return None

        path = os.path.join(self.test_case_dir, self.get_path(tcid), work_item_id, "workitem.xml")
        try:
            tree = etree.parse(path)
        # pylint: disable=broad-except
        except Exception:
            logger.warning("Couldn't load workitem %s", work_item_id)
            self._cache[work_item_id] = InvalidObject()
            return None
        return tree

    @staticmethod
    def _get_steps(item):
        steps = []
        expected_results = []

        steps_list = item.xpath('.//item[@id = "steps"]')
        if not steps_list:
            return steps, expected_results

        steps_list = steps_list[0]
        steps_items = steps_list.xpath(".//item[@text-type]")
        for index, rec in enumerate(steps_items):
            if index % 2 == 0:
                steps.append(rec.text)
            else:
                expected_results.append(rec.text)
        return steps, expected_results

    @staticmethod
    def _get_linked_items(item):
        linked = []
        linked_items = item.xpath("./list/struct")
        for struct in linked_items:
            role_found = False
            struct_item = None

            for litem in struct:
                attrib = litem.attrib["id"]
                if attrib == "role":
                    if litem.text == "verifies":
                        role_found = True
                    else:
                        break
                elif attrib == "workItem":
                    struct_item = litem.text

            if role_found and struct_item:
                linked.append(struct_item)

        return linked

    def __getitem__(self, work_item_id):
        if work_item_id in self._cache:
            return self._cache[work_item_id]
        elif isinstance(self._cache[work_item_id], InvalidObject):
            return None

        tree = self.get_tree(work_item_id)
        if not tree:
            return None

        for item in tree.xpath("/work-item/field"):
            attrib = item.attrib["id"]
            if attrib == "testSteps":
                steps, results = self._get_steps(item)
                self._cache[work_item_id]["testSteps"] = steps
                self._cache[work_item_id]["expectedResults"] = results
            elif attrib == "linkedWorkItems":
                self._cache[work_item_id]["linkedWorkItems"] = self._get_linked_items(item)
            else:
                self._cache[work_item_id][item.attrib["id"]] = item.text

        self._cache[work_item_id]["work_item_id"] = work_item_id
        if "assignee" not in self._cache[work_item_id]:
            self._cache[work_item_id]["assignee"] = ""
        if "title" not in self._cache[work_item_id]:
            logger.debug("Workitem %s has no title", work_item_id)

        return self._cache[work_item_id]

    def get_all_items(self):
        """Walks the repo and returns work items."""
        for item in os.walk(self.test_case_dir):
            if "workitem.xml" not in item[2]:
                continue
            case_id = os.path.split(item[0])[-1]
            if not (case_id and "*" not in case_id):
                continue
            item_cache = self[case_id]
            if not item_cache:
                continue
            if not item_cache.get("title"):
                continue
            yield item_cache
