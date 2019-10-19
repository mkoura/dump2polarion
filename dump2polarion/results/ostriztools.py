"""Helper functions for handling JSON data from Ostriz."""

import datetime
import json
import logging
import os
from collections import OrderedDict

import requests
from packaging.version import InvalidVersion, Version

from dump2polarion.exceptions import Dump2PolarionException, NothingToDoException
from dump2polarion.exporters import xunit_exporter

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


IGNORED_PARAMS = {"browserVersion", "browserPlatform", "browserName"}


def _get_json(location):
    """Read JSON data from file or URL."""
    location = os.path.expanduser(location)
    try:
        if os.path.isfile(location):
            with open(location, encoding="utf-8") as json_data:
                return json.load(json_data, object_pairs_hook=OrderedDict).get("tests")
        elif location.startswith("http"):
            json_data = requests.get(location)
            if not json_data:
                raise Dump2PolarionException("Failed to download")
            return json.loads(json_data.text, object_pairs_hook=OrderedDict).get("tests")
        else:
            raise Dump2PolarionException("Invalid location")
    except Exception as err:
        raise Dump2PolarionException("Failed to parse JSON from {}: {}".format(location, err))


def _get_testrun_id(version):
    """Get testrun id out of the version string.

    Remove trailing version dates / hashes separated by - / _
    Then use packaging Version to parse the version string
    Then cast each release component to string for joining with _

    Build and return testrun ID that looks like x_y_z_a from version x.y.z.a-20181114_abcdef
    """
    try:
        v = Version(version.split("-")[0].split("_")[0])
        build_base = "_".join([str(i) for i in v.release])
    except InvalidVersion:
        raise Dump2PolarionException("InvalidVersion parsing testrun ID from {}".format(version))
    except Exception:
        # not in expected format
        raise Dump2PolarionException("Exception parsing testrun ID from {}".format(version))
    return build_base


def _calculate_duration(start_time, finish_time):
    """Calculate how long it took to execute the testcase."""
    if not (start_time and finish_time):
        return 0
    start = datetime.datetime.fromtimestamp(start_time)
    finish = datetime.datetime.fromtimestamp(finish_time)
    duration = finish - start

    decimals = float("0." + str(duration.microseconds))
    return duration.seconds + decimals


def _get_testname(test_path):
    """Get test name out of full test path."""
    path_end = test_path.find(".py/")
    if path_end:
        offset = path_end + 4
        return test_path[offset:]
    return None


def _filter_parameters(parameters):
    """Filter the ignored parameters out."""
    if not parameters:
        return None
    return OrderedDict(
        (param, value) for param, value in parameters.items() if param not in IGNORED_PARAMS
    )


def _append_record(test_data, results, test_path):
    """Add data of single testcase results to results database.

    TODO: Make blocker skips more consistent in where the reason for blocking is stored in ostriz
    """
    statuses = test_data.get("statuses")
    jenkins_data = test_data.get("jenkins", {})
    skipped = test_data.get("skipped", {})  # only set for setup skips

    # setup a comment for uploading blockers
    comment = ""
    if skipped.get("type") == "blocker":
        # skipped testcase because of blocker
        # BZ's in reason, others in issues coming from ostriz json
        # urls stored in issues when  its a GH blocker
        reason = skipped.get("reason") or test_data.get("issues")

        if reason:
            if not isinstance(reason, str):
                reason = ", ".join([str(r) for r in reason])  # keys if its a dict, should be list
            comment = "blocker: {}".format(reason)
        else:
            comment = "Couldn't find reason for blocker skip"

    data = [
        ("title", test_data.get("test_name") or _get_testname(test_path)),
        ("verdict", statuses.get("overall")),
        ("source", test_data.get("source")),
        ("job_name", jenkins_data.get("job_name")),
        ("run", jenkins_data.get("build_number")),
        ("comment", comment),
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
    """Read the content of the input JSON and return testcases results."""
    if not ostriz_data:
        raise NothingToDoException("No data to import")

    results = []
    found_build = None
    last_finish_time = [0]
    for test_path, test_data in ostriz_data.items():
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
    """Read Ostriz's data and return imported data."""
    ostriz_data = _get_json(location)
    return _parse_ostriz(ostriz_data)
