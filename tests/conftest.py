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
