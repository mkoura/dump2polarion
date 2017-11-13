# encoding: utf-8
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods

from __future__ import unicode_literals

import io
import logging

import pytest


@pytest.fixture(scope='module')
def config_prop():
    return {
        'xunit_import_properties': {
            'polarion-dry-run': False,
            'polarion-project-id': 'RHCF3',
            'polarion-testrun-status-id': 'inprogress',
            'polarion-response-test': 'test'
        },
        'message_bus': 'ci-bus.example.com:6000',
        'xunit_target': 'https://polarion.example.com/import/xunit',
        'testcase_taget': 'https://polarion.example.com/import/testcase'
    }


@pytest.fixture(scope='function')
def config_e2e(tmpdir):
    conf_content = """
xunit_import_properties:
    polarion-dry-run            : false
    polarion-project-id         : RHCF3
    polarion-testrun-status-id  : inprogress
    polarion-response-test      : test
message_bus: ci-bus.example.com:6000
xunit_target: https://polarion.example.com/import/xunit
testcase_taget: https://polarion.example.com/import/testcase
"""
    conf_file = tmpdir.join('dump2polarion.yaml')
    conf_file.write(conf_content)
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
