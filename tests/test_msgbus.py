# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access,invalid-name

from __future__ import unicode_literals

import threading
import time

from dump2polarion import msgbus


class TestMsgBusListener(object):
    def test_message_received(self):
        listener = msgbus._XunitListener()

        def _msg_received():
            time.sleep(0.05)
            listener.on_message('header', 'message')

        threading.Thread(target=_msg_received).start()
        retval = listener.wait_for_message()
        assert retval

    def test_message_not_received(self):
        listener = msgbus._XunitListener()
        retval = listener.wait_for_message(0.01)
        assert retval is False

    def test_on_message(self):
        listener = msgbus._XunitListener()
        threading.Thread(target=listener.wait_for_message, args=(0.05,)).start()
        listener.on_message('header', 'message')
        assert listener.message_list[0] == ('header', 'message', False)

    def test_on_error(self):
        listener = msgbus._XunitListener()
        threading.Thread(target=listener.wait_for_message, args=(0.05,)).start()
        listener.on_error('header', 'message')
        assert listener.message_list[0] == ('header', 'message', True)

    def test_lastest_message(self):
        listener = msgbus._XunitListener()
        threading.Thread(target=listener.wait_for_message, args=(0.05,)).start()
        listener.on_message('header', 'message')
        assert listener.get_latest_message() == ('header', 'message', False)


class TestMsgBusOutcome(object):
    def test_is_error_none(self, captured_log):
        assert msgbus._check_outcome('', None) is False
        assert 'Submit verification timed out' in captured_log.getvalue()

    def test_is_error_true(self, captured_log):
        assert msgbus._check_outcome('', True) is False
        assert 'Received an error' in captured_log.getvalue()

    def test_invalid_json(self, captured_log):
        assert msgbus._check_outcome('', False) is False
        assert 'Cannot parse message' in captured_log.getvalue()

    def test_submit_log(self, captured_log):
        assert msgbus._check_outcome('{ "log-url": "submit-log" }', False) is False
        assert 'Submit log: submit-log' in captured_log.getvalue()

    def test_status_passed(self, captured_log):
        assert msgbus._check_outcome('{ "status": "passed" }', False) is True
        assert 'Results successfully submitted' in captured_log.getvalue()

    def test_status_failed(self, captured_log):
        assert msgbus._check_outcome('{ "status": "failed" }', False) is False
        assert 'Status = failed, results not updated' in captured_log.getvalue()


class TestMsgBusVerification(object):
    def test_missing_bus_url(self, captured_log):
        assert msgbus.get_verification_func(None, None, None, None) is None
        assert 'not configured, skipping submit verification' in captured_log.getvalue()

    def test_invalid_xml(self, captured_log):
        assert msgbus.get_verification_func('foo', None, None, None) is None
        assert 'The response property is not set, skipping' in captured_log.getvalue()

    def test_missing_credentials(self, captured_log):
        assert msgbus.get_verification_func('foo', ('test', 'test'), None, None) is None
        assert 'Missing credentials, skipping' in captured_log.getvalue()
