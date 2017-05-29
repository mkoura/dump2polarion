#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Polarion® dumper for CFME Jenkins
"""

from __future__ import unicode_literals, absolute_import

import sys

from dump2polarion.dumper_cli import main


def get_testrun_id(version_file):
    """Gets testrun id out of the appliance_version file."""
    with open(version_file) as input_file:
        version = input_file.read().strip()
    try:
        build_base = version.replace('.', '_')
        build_last_num = int(build_base.split('_')[3])
    # pylint: disable=broad-except
    except Exception:
        return
    if build_last_num < 10:
        pad_build = build_base[-1].zfill(2)
        return build_base[:-1] + pad_build
    return build_base


def make_args():
    """Makes args for polarion_dumper."""
    new_argv = sys.argv[1:]
    for index, arg in enumerate(new_argv):
        if arg in ('-t', '--testrun-id'):
            break
    else:
        index = None
    if index:
        new_argv[index + 1] = get_testrun_id(new_argv[index + 1])

    return new_argv


if __name__ == '__main__':
    sys.exit(main(make_args()))
