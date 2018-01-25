# -*- coding: utf-8 -*-
"""
Helper functions for handling JSON data from Ostriz.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import io
import json
import os

from collections import OrderedDict

import requests

from dump2polarion import exporter
from dump2polarion.exceptions import Dump2PolarionException


def _get_json(location):
    """Reads JSON data from file or URL."""
    location = os.path.expanduser(location)
    try:
        if os.path.isfile(location):
            with io.open(location, encoding='utf-8') as json_data:
                return json.load(json_data, object_pairs_hook=OrderedDict).get('tests')
        elif 'http' in location:
            json_data = requests.get(location)
            if not json_data:
                raise Dump2PolarionException("Failed to download")
            return json.loads(json_data.text, object_pairs_hook=OrderedDict).get('tests')
        else:
            raise Dump2PolarionException("Invalid location")
    except Exception as err:
        raise Dump2PolarionException(
            "Failed to parse JSON from {}: {}".format(location, err))


def _get_testrun_id(version):
    """Gets testrun id out of the appliance_version file."""
    try:
        build_base = version.strip().split('-')[0].split('_')[0].replace('.', '_')
        zval = int(build_base.split('_')[3])
    except Exception:
        # not in expected format
        raise Dump2PolarionException("Cannot find testrun id")
    if zval < 10:
        pad_build = build_base[-1].zfill(2)
        return build_base[:-1] + pad_build
    return build_base


def _calculate_duration(start_time, finish_time):
    """Calculates how long it took to execute the testcase."""
    if not(start_time and finish_time):
        return 0
    start = datetime.datetime.fromtimestamp(start_time)
    finish = datetime.datetime.fromtimestamp(finish_time)
    duration = finish - start

    microseconds = float(('0.' + str(duration.microseconds)))
    return duration.seconds + microseconds


def _parse_ostriz(ostriz_data):
    """Reads the content of the input JSON and returns testcases results."""
    if not ostriz_data:
        raise Dump2PolarionException("No data to import")

    results = []
    found_version = None
    for test_data in ostriz_data.values():
        # make sure we are collecting data for the same appliance version
        if found_version:
            if found_version != test_data.get('version'):
                continue
        else:
            found_version = test_data.get('version')
        statuses = test_data.get('statuses')
        if not statuses:
            continue

        data = [
            ('title', test_data.get('test_name')),
            ('verdict', statuses.get('overall')),
            ('time', _calculate_duration(
                test_data.get('start_time'), test_data.get('finish_time')) or 0)
        ]
        test_id = test_data.get('test_id')
        if test_id:
            data.append(('id', test_id))

        results.append(OrderedDict(data))

    testrun_id = _get_testrun_id(found_version)
    return exporter.ImportedData(results=results, testrun=testrun_id)


# pylint: disable=unused-argument
def import_ostriz(location, **kwargs):
    """Reads Ostriz's data and returns imported data."""
    ostriz_data = _get_json(location)
    return _parse_ostriz(ostriz_data)
