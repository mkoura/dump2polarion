# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import pytest


@pytest.fixture(scope='module')
def config_prop():
    return {
        'xunit_import_properties': {
            'polarion-dry-run': False,
            'polarion-project-id': 'RHCF3',
            'polarion-testrun-status-id': 'inprogress',
            'polarion-response-test': 'test'
        }
    }


@pytest.fixture(scope='function')
def config_e2e(tmpdir):
    conf_content = """
xunit_import_properties:
    polarion-dry-run            : false
    polarion-project-id         : RHCF3
    polarion-testrun-status-id  : inprogress
    polarion-response-test      : test
"""
    conf_file = tmpdir.join('dump2polarion.yaml')
    conf_file.write(conf_content)
    return str(conf_file)
