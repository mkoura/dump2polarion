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

_RESULT_SEARCH = re.compile(r"Work item: '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)$")
_RESULT_WARN_SEARCH = re.compile(r" '(test_[^']+|[A-Z][^']+)'\.$")

_TESTCASE_SEARCH = re.compile(r" test case '(test_[^']+|[A-Z][^']+)' \(([^)]+)\)")
_TESTCASE_WARN_SEARCH = _RESULT_WARN_SEARCH

_REQ_SEARCH = re.compile(r" requirement '([a-zA-Z][^']+)' \(([^)/]+)")
_REQ_WARN_SEARCH = re.compile(r" '([^']+)'\.$")


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


def get_result(line):
    """Gets work item name and id."""
    res = _RESULT_SEARCH.search(line)
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


def get_result_warn(line):
    """Gets work item name of item that was not successfully imported."""
    res = _RESULT_WARN_SEARCH.search(line)
    try:
        return LogItem(res.group(1), None, None)
    except (AttributeError, IndexError):
        return None


def get_testcase(line):
    """Gets test case name and id."""
    res = _TESTCASE_SEARCH.search(line)
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


def get_testcase_warn(line):
    """Gets name of test case that was not successfully imported."""
    res = _TESTCASE_WARN_SEARCH.search(line)
    try:
        return LogItem(res.group(1), None, None)
    except (AttributeError, IndexError):
        return None


def get_requirement(line):
    """Gets requirement name and id."""
    res = _REQ_SEARCH.search(line)
    try:
        name, tc_id = res.group(1), res.group(2)
    except (AttributeError, IndexError):
        return None

    return LogItem(name, tc_id, None)


def get_requirement_warn(line):
    """Gets name of test case that was not successfully imported."""
    res = _REQ_WARN_SEARCH.search(line)
    try:
        return LogItem(res.group(1), None, None)
    except (AttributeError, IndexError):
        return None


def parse_xunit(fp, log_file):
    """Parse log file produced by the XUnit Iporter."""
    existing_items = []
    duplicate_items = []
    new_items = []
    for line in fp:
        line = line.strip()
        if "Work item: " in line:
            existing_it = get_result(line)
            if existing_it:
                existing_items.append(existing_it)
        elif "Unable to find *unique* work item" in line:
            duplicate_it = get_result_warn(line)
            if duplicate_it:
                duplicate_items.append(duplicate_it)
        elif "Unable to find work item for" in line:
            new_it = get_result_warn(line)
            if new_it:
                new_items.append(new_it)

    outcome = ParsedLog("xunit", new_items, existing_items, duplicate_items)

    if not outcome:
        raise Dump2PolarionException("No valid data found in the log file '{}'".format(log_file))

    return outcome


def parse_testcase(fp, log_file):
    """Parse log file produced by the Test Case Importer."""
    existing_items = []
    duplicate_items = []
    new_items = []
    for line in fp:
        line = line.strip()
        if "Updated test case" in line:
            existing_it = get_testcase(line)
            if existing_it:
                existing_items.append(existing_it)
        elif "Found multiple work items with the title" in line:
            duplicate_it = get_testcase_warn(line)
            if duplicate_it:
                duplicate_items.append(duplicate_it)
        elif "Created test case" in line:
            new_it = get_testcase(line)
            if new_it:
                new_items.append(new_it)

    outcome = ParsedLog("testcase", new_items, existing_items, duplicate_items)

    if not outcome:
        raise Dump2PolarionException("No valid data found in the log file '{}'".format(log_file))

    return outcome


def parse_requirements(fp, log_file):
    """Parse log file produced by the Requirements Importer."""
    existing_items = []
    duplicate_items = []
    new_items = []
    for line in fp:
        line = line.strip()
        if "Updated requirement" in line:
            existing_it = get_requirement(line)
            if existing_it:
                existing_items.append(existing_it)
        elif "Found multiple work items with the title" in line:
            duplicate_it = get_requirement_warn(line)
            if duplicate_it:
                duplicate_items.append(duplicate_it)
        elif "Created requirement" in line:
            new_it = get_requirement(line)
            if new_it:
                new_items.append(new_it)

    outcome = ParsedLog("requirement", new_items, existing_items, duplicate_items)

    if not outcome:
        raise Dump2PolarionException("No valid data found in the log file '{}'".format(log_file))

    return outcome


def parse(log_file):
    """Parse log file."""
    with io.open(os.path.expanduser(log_file), encoding="utf-8") as input_file:
        for line in input_file:
            if "Starting import of XUnit results" in line:
                handler = parse_xunit
                break
            elif "Starting import of test cases" in line:
                handler = parse_testcase
                break
            elif "Starting import of requirements" in line:
                handler = parse_requirements
                break
        else:
            raise Dump2PolarionException(
                "No valid data found in the log file '{}'".format(log_file)
            )

        return handler(input_file, log_file)
