# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,too-few-public-methods


from __future__ import unicode_literals

import io
import os

from mock import Mock, patch
from tests import conf

from dump2polarion import submit


class TestSubmit(object):
    def test_missing_input(self, captured_log):
        with patch('requests.post'):
            submit.submit('')
        assert 'no data supplied' in captured_log.getvalue()

    def test_missing_credentials(self, captured_log):
        with patch('requests.post'):
            submit.submit('foo')
        assert 'missing credentials' in captured_log.getvalue()

    def test_missing_target(self, captured_log):
        with patch('requests.post'):
            submit.submit('foo', user='john', password='123')
        assert 'submit target not found' in captured_log.getvalue()

    def test_missing_testrun_id(self, captured_log):
        with patch('requests.post'):
            submit.submit('<testsuites', user='john', password='123')
        assert 'missing testrun id' in captured_log.getvalue()

    def test_fill_testrun_id(self):
        fname = 'properties.xml'
        with io.open(os.path.join(conf.DATA_PATH, fname), encoding='utf-8') as input_xml:
            parsed = input_xml.read()
        filled = submit._fill_testrun_id(parsed, '5_8_0_17')
        assert 'name="polarion-testrun-id" value="5_8_0_17"' in filled

    def test_fill_testrun_submit(self):
        fname = 'properties.xml'
        with patch('requests.post'):
            submit.submit(
                xml_file=os.path.join(conf.DATA_PATH, fname),
                testrun_id='5_8_0_17',
                user='john',
                password='123')

    def test_get_testcases_taget(self, config_prop):
        response = submit._get_submit_target('<testcases', config_prop)
        assert 'testcase' in response

    def test_get_testsuites_taget(self, config_prop):
        response = submit._get_submit_target('<testsuites', config_prop)
        assert 'xunit' in response

    def test_file_testsuites_failure(self, captured_log):
        class Response(object):
            def __init__(self):
                self.status_code = 404

            def __len__(self):
                return 0

        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post', return_value=Response()):
            response = submit.submit(xml_file=input_file, user='john', password='123')
        assert not response
        assert 'HTTP status 404: failed to submit results' in captured_log.getvalue()

    def test_file_testsuites_none(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post', return_value=None):
            response = submit.submit(xml_file=input_file, user='john', password='123')
        assert not response
        assert 'Failed to submit results' in captured_log.getvalue()

    def test_file_testsuites_exception(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post', side_effect=KeyError('request failed')):
            response = submit.submit(xml_file=input_file, user='john', password='123')
        assert not response
        assert 'request failed' in captured_log.getvalue()
        assert 'Failed to submit results' in captured_log.getvalue()

    def test_file_testsuites_success(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post'):
            response = submit.submit(xml_file=input_file, user='john', password='123')
        assert response
        assert 'Results received' in captured_log.getvalue()


class TestSubmitAndVerify(object):
    def test_missing_input(self, captured_log):
        with patch('requests.post'):
            submit.submit_and_verify('')
        assert 'no data supplied' in captured_log.getvalue()

    def test_verify_none(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post'), \
                patch('dump2polarion.msgbus.get_verification_func', return_value=None):
            response = submit.submit_and_verify(xml_file=input_file, user='john', password='123')
        assert response
        assert 'Results received' in captured_log.getvalue()

    def test_verify_skipped(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post'):
            response = submit.submit_and_verify(
                xml_file=input_file, user='john', password='123', no_verify=True)
        assert response
        assert 'Results received' in captured_log.getvalue()

    def test_verify_failed(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post'), \
                patch('dump2polarion.msgbus.get_verification_func',
                      return_value=Mock(return_value=False)):
            response = submit.submit_and_verify(xml_file=input_file, user='john', password='123')
        assert not response
        assert 'Results received' in captured_log.getvalue()

    def test_verify_success(self, captured_log):
        input_file = os.path.join(conf.DATA_PATH, 'complete_transform.xml')
        with patch('requests.post'), \
                patch('dump2polarion.msgbus.get_verification_func',
                      return_value=Mock()):
            response = submit.submit_and_verify(xml_file=input_file, user='john', password='123')
        assert response
        assert 'Results received' in captured_log.getvalue()
