# -*- coding: utf-8 -*-
"""
Find out info about work items in Polarion by parsing logs produced by Importers.

Find out what items:
  * exists (and can be updated)
  * are new (or need to be created)
  * have duplicates
  * Polarion IDs of existing items

Logs can be produced by submitting XMLs with dry-only.
"""

from __future__ import absolute_import, unicode_literals

import io
import os
import re

from dump2polarion.exceptions import Dump2PolarionException


class LogItem(object):
    """Represents one work item record in a log file."""

    # pylint: disable=redefined-builtin
    def __init__(self, name, id, custom_id):
        self.name = name
        self.id = id
        self.custom_id = custom_id

    def __repr__(self):
        return "<LogItem {}>".format(self.name)


class ParsedLog(object):
    """Outcome of log parsing."""

    def __init__(self, log_type, new_items, existing_items, duplicate_items):
        self.log_type = log_type
        self.new_items = new_items
        self.existing_items = existing_items
        self.duplicate_items = duplicate_items

    def __len__(self):
        return 1 if (self.new_items or self.existing_items or self.duplicate_items) else 0

    def __repr__(self):
        return "<ParsedLog {}>".format(self.log_type)


class XUnitParser(object):
    """Parser for XUnit logs."""

    RESULT_SEARCH = re.compile(r"Work item: '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)$")
    RESULT_WARN_SEARCH = re.compile(r" '(test_[^']+|[A-Z][^']+)'\.$")
    RESULT_WARN_SEARCH_CUSTOM = re.compile(r" '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)\.$")

    def __init__(self, fp, log_file):
        self.fp = fp
        self.log_file = log_file

    def get_result(self, line):
        """Gets work item name and id."""
        res = self.RESULT_SEARCH.search(line)
        try:
            name, ids = res.group(1), res.group(2)
        except (AttributeError, IndexError):
            return None

        ids = ids.split("/")
        tc_id = ids[0]
        try:
            custom_id = ids[1]
        except IndexError:
            custom_id = None
        return LogItem(name, tc_id, custom_id)

    def get_result_warn(self, line):
        """Gets work item name of item that was not successfully imported."""
        res = self.RESULT_WARN_SEARCH.search(line)
        try:
            return LogItem(res.group(1), None, None)
        except (AttributeError, IndexError):
            pass

        # try again with custom ID
        res = self.RESULT_WARN_SEARCH_CUSTOM.search(line)
        try:
            return LogItem(res.group(1), None, res.group(2))
        except (AttributeError, IndexError):
            return None

    def parse(self):
        """Parse log file produced by the XUnit Iporter."""
        existing_items = []
        duplicate_items = []
        new_items = []
        for line in self.fp:
            line = line.strip()
            if "Work item: " in line:
                existing_it = self.get_result(line)
                if existing_it:
                    existing_items.append(existing_it)
            elif "Unable to find *unique* work item" in line:
                duplicate_it = self.get_result_warn(line)
                if duplicate_it:
                    duplicate_items.append(duplicate_it)
            elif "Unable to find work item for" in line:
                new_it = self.get_result_warn(line)
                if new_it:
                    new_items.append(new_it)

        outcome = ParsedLog("xunit", new_items, existing_items, duplicate_items)

        if not outcome:
            raise Dump2PolarionException(
                "No valid data found in the log file '{}'".format(self.log_file)
            )

        return outcome


class TestcasesParser(object):
    """Parser for Testcase logs."""

    TESTCASE_SEARCH = re.compile(r" test case '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)")
    TESTCASE_WARN_SEARCH = re.compile(r" '(test_[^']+|[A-Z][^']+)'\.$")

    def __init__(self, fp, log_file):
        self.fp = fp
        self.log_file = log_file

    def get_testcase(self, line):
        """Gets test case name and id."""
        res = self.TESTCASE_SEARCH.search(line)
        try:
            name, ids = res.group(1), res.group(2)
        except (AttributeError, IndexError):
            return None

        ids = ids.split("/")
        tc_id = ids[0]
        try:
            custom_id = ids[1]
        except IndexError:
            custom_id = None
        return LogItem(name, tc_id, custom_id)

    def get_testcase_warn(self, line):
        """Gets name of test case that was not successfully imported."""
        res = self.TESTCASE_WARN_SEARCH.search(line)
        try:
            return LogItem(res.group(1), None, None)
        except (AttributeError, IndexError):
            return None

    def parse(self):
        """Parse log file produced by the Test Case Importer."""
        existing_items = []
        duplicate_items = []
        new_items = []
        for line in self.fp:
            line = line.strip()
            if "Updated test case" in line:
                existing_it = self.get_testcase(line)
                if existing_it:
                    existing_items.append(existing_it)
            elif "Found multiple work items with the title" in line:
                duplicate_it = self.get_testcase_warn(line)
                if duplicate_it:
                    duplicate_items.append(duplicate_it)
            elif "Created test case" in line:
                new_it = self.get_testcase(line)
                if new_it:
                    new_items.append(new_it)

        outcome = ParsedLog("testcase", new_items, existing_items, duplicate_items)

        if not outcome:
            raise Dump2PolarionException(
                "No valid data found in the log file '{}'".format(self.log_file)
            )

        return outcome


class RequirementsParser(object):
    """Parser for Requirement logs."""

    REQ_SEARCH = re.compile(r" requirement '([a-zA-Z][^']+)' \(([^)/]+)")
    REQ_WARN_SEARCH = re.compile(r" '([^']+)'\.$")

    def __init__(self, fp, log_file):
        self.fp = fp
        self.log_file = log_file

    def get_requirement(self, line):
        """Gets requirement name and id."""
        res = self.REQ_SEARCH.search(line)
        try:
            name, tc_id = res.group(1), res.group(2)
        except (AttributeError, IndexError):
            return None

        return LogItem(name, tc_id, None)

    def get_requirement_warn(self, line):
        """Gets name of test case that was not successfully imported."""
        res = self.REQ_WARN_SEARCH.search(line)
        try:
            return LogItem(res.group(1), None, None)
        except (AttributeError, IndexError):
            return None

    def parse(self):
        """Parse log file produced by the Requirements Importer."""
        existing_items = []
        duplicate_items = []
        new_items = []
        for line in self.fp:
            line = line.strip()
            if "Updated requirement" in line:
                existing_it = self.get_requirement(line)
                if existing_it:
                    existing_items.append(existing_it)
            elif "Found multiple work items with the title" in line:
                duplicate_it = self.get_requirement_warn(line)
                if duplicate_it:
                    duplicate_items.append(duplicate_it)
            elif "Created requirement" in line:
                new_it = self.get_requirement(line)
                if new_it:
                    new_items.append(new_it)

        outcome = ParsedLog("requirement", new_items, existing_items, duplicate_items)

        if not outcome:
            raise Dump2PolarionException(
                "No valid data found in the log file '{}'".format(self.log_file)
            )

        return outcome


def parse(log_file):
    """Parse log file."""
    with io.open(os.path.expanduser(log_file), encoding="utf-8") as input_file:
        for line in input_file:
            if "Starting import of XUnit results" in line:
                obj = XUnitParser
                break
            elif "Starting import of test cases" in line:
                obj = TestcasesParser
                break
            elif "Starting import of requirements" in line:
                obj = RequirementsParser
                break
        else:
            raise Dump2PolarionException(
                "No valid data found in the log file '{}'".format(log_file)
            )

        return obj(input_file, log_file).parse()
