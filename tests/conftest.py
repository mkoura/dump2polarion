# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import io
import os
import logging

import pytest

from tests import conf


GENERIC_CONF = {
    'xunit_target': 'https://polarion.example.com/import/xunit',
    'testcase_taget': 'https://polarion.example.com/import/testcase',
    'xunit_queue': 'https://polarion.example.com/import/xunit-queue',
    'testcase_queue': 'https://polarion.example.com/import/testcase-queue'
}

RHCF3_PROPS = {
    'polarion-dry-run': False,
    'polarion-project-id': 'RHCF3',
    'polarion-testrun-status-id': 'inprogress',
    'polarion-response-test': 'test'
}

RHCF3_CONF = GENERIC_CONF.copy()
RHCF3_CONF['xunit_import_properties'] = RHCF3_PROPS

CMP_CONF = GENERIC_CONF.copy()
CMP_CONF['xunit_import_properties'] = RHCF3_PROPS.copy()
CMP_CONF['xunit_import_properties']['polarion-project-id'] = 'CMP'


@pytest.fixture(scope='module')
def config_prop():
    return RHCF3_CONF


@pytest.fixture(scope='module')
def config_prop_cmp():
    return CMP_CONF


@pytest.fixture(scope='function')
def config_e2e():
    conf_file = os.path.join(conf.DATA_PATH, 'dump2polarion.yaml')
    return str(conf_file)


class SimpleFormatter(object):
    def format(self, record):
        message = record.getMessage()
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        return message


@pytest.yield_fixture
def captured_log():
    buff = io.StringIO()
    handler = logging.StreamHandler(buff)
    handler.setFormatter(SimpleFormatter())

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield buff

    logger.handlers.remove(handler)


@pytest.fixture(autouse=True)
def no_user_conf(monkeypatch):
    monkeypatch.setattr('dump2polarion.configuration.DEFAULT_USER_CONF', '')
