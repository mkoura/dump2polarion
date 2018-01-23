# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import io
import os
import logging

import pytest

from tests import conf


@pytest.fixture(scope='module')
def config_prop():
    return {
        'xunit_import_properties': {
            'polarion-dry-run': False,
            'polarion-project-id': 'RHCF3',
            'polarion-testrun-status-id': 'inprogress',
            'polarion-response-test': 'test'
        },
        'xunit_target': 'https://polarion.example.com/import/xunit',
        'testcase_taget': 'https://polarion.example.com/import/testcase',
        'xunit_queue': 'https://polarion.example.com/import/xunit-queue',
        'testcase_queue': 'https://polarion.example.com/import/testcase-queue'
    }


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
