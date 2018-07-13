# -*- coding: utf-8 -*-
"""
Helper functions for handling JSON data from Ostriz.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import io
import json
import logging
import os
from collections import OrderedDict

import requests
import six

from dump2polarion import xunit_exporter
from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


IGNORED_PARAMS = {"browserVersion", "browserPlatform", "browserName"}


def _get_json(location):
    """Reads JSON data from file or URL."""
    location = os.path.expanduser(location)
    try:
        if os.path.isfile(location):
            with io.open(location, encoding="utf-8") as json_data:
                return json.load(json_data, object_pairs_hook=OrderedDict).get("tests")
        elif "http" in location:
            json_data = requests.get(location)
            if not json_data:
                raise Dump2PolarionException("Failed to download")
            return json.loads(json_data.text, object_pairs_hook=OrderedDict).get("tests")
        else:
            raise Dump2PolarionException("Invalid location")
    except Exception as err:
        raise Dump2PolarionException("Failed to parse JSON from {}: {}".format(location, err))


def _get_testrun_id(version):
    """Gets testrun id out of the appliance_version file."""
    try:
        build_base = version.strip().split("-")[0].split("_")[0].replace(".", "_")
        zval = int(build_base.split("_")[3])
    except Exception:
        # not in expected format
        raise Dump2PolarionException("Cannot find testrun id")
    if zval < 10:
        pad_build = build_base[-1].zfill(2)
        return build_base[:-1] + pad_build
    return build_base


def _calculate_duration(start_time, finish_time):
    """Calculates how long it took to execute the testcase."""
    if not (start_time and finish_time):
        return 0
    start = datetime.datetime.fromtimestamp(start_time)
    finish = datetime.datetime.fromtimestamp(finish_time)
    duration = finish - start

    decimals = float(("0." + str(duration.microseconds)))
    return duration.seconds + decimals


def _get_testname(test_path):
    """Gets test name out of full test path."""
    path_end = test_path.find(".py/")
    if path_end:
        offset = path_end + 4
        return test_path[offset:]
    return None


def _filter_parameters(parameters):
    """Filters the ignored parameters out."""
    if not parameters:
        return None
    return OrderedDict(
        (param, value) for param, value in six.iteritems(parameters) if param not in IGNORED_PARAMS
    )


def _append_record(test_data, results, test_path):
    """Adds data of single testcase results to results database."""
    statuses = test_data.get("statuses")
    jenkins_data = test_data.get("jenkins") or {}

    data = [
        ("title", test_data.get("test_name") or _get_testname(test_path)),
        ("verdict", statuses.get("overall")),
        ("source", test_data.get("source")),
        ("job_name", jenkins_data.get("job_name")),
        ("run", jenkins_data.get("build_number")),
        ("params", _filter_parameters(test_data.get("params"))),
        (
            "time",
            _calculate_duration(test_data.get("start_time"), test_data.get("finish_time")) or 0,
        ),
    ]
    test_id = test_data.get("polarion")
    if test_id:
        if isinstance(test_id, list):
            test_id = test_id[0]
        data.append(("test_id", test_id))

    results.append(OrderedDict(data))


def _comp_finish_time(test_data, last_finish_time):
    curr_finish_time = test_data.get("finish_time") or 0
    if curr_finish_time > last_finish_time[0]:
        last_finish_time[0] = curr_finish_time


def _parse_ostriz(ostriz_data):
    """Reads the content of the input JSON and returns testcases results."""
    if not ostriz_data:
        raise NothingToDoException("No data to import")

    results = []
    found_build = None
    last_finish_time = [0]
    for test_path, test_data in six.iteritems(ostriz_data):
        curr_build = test_data.get("build")
        if not curr_build:
            continue

        # set `found_build` from first record where it's present
        if not found_build:
            found_build = curr_build

        # make sure we are collecting data for the same build
        if found_build != curr_build:
            continue

        if not test_data.get("statuses"):
            continue

        _append_record(test_data, results, test_path)
        _comp_finish_time(test_data, last_finish_time)

    if last_finish_time[0]:
        logger.info("Last result finished at %s", last_finish_time[0])

    testrun_id = _get_testrun_id(found_build)
    return xunit_exporter.ImportedData(results=results, testrun=testrun_id)


# pylint: disable=unused-argument
def import_ostriz(location, **kwargs):
    """Reads Ostriz's data and returns imported data."""
    ostriz_data = _get_json(location)
    return _parse_ostriz(ostriz_data)
