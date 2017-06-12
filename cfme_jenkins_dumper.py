#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Polarion dumper for CFME Jenkins
"""

from __future__ import unicode_literals, absolute_import, print_function

import sys

from dump2polarion.dumper_cli import main


def get_testrun_id(version_file):
    """Gets testrun id out of the appliance_version file."""
    with open(version_file) as input_file:
        version = input_file.read().strip()
        version = version.split('-')[0].split('_')[0]
        build_base = version.replace('.', '_')
    try:
        zval = int(build_base.split('_')[3])
    except (IndexError, ValueError):
        # not in expected format
        return
    if zval < 10:
        pad_build = build_base[-1].zfill(2)
        return build_base[:-1] + pad_build
    return build_base


def tweak_args():
    """Tweaks args for polarion dumper."""
    new_argv = sys.argv[1:]

    for index, arg in enumerate(new_argv):
        if arg in ('-t', '--testrun-id'):
            break
    else:
        index = None

    testrun_id = get_testrun_id(new_argv[index + 1])
    if not testrun_id:
        print("Cannot find testrun id.", file=sys.stderr)
        sys.exit(1)

    # replace `-t appliance_version` with `-t testrun_id`
    new_argv[index + 1] = testrun_id

    return new_argv


if __name__ == '__main__':
    sys.exit(main(tweak_args()))
