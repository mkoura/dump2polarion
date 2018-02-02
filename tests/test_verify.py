# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access,invalid-name

from __future__ import unicode_literals

import os

from mock import patch

from dump2polarion import verify


LAST_ID = {
    "jobs": [{
        "id": 17975
    }]
}

SEARCH_QUEUE = {
    "jobsPerPage": 50,
    "maxPages": 2,
    "currentPage": 1,
    "jobs": [{
        "id": 17977,
        "status": "SUCCESS",
        "logstashURL": "http://logstash/00017977.log"
    }, {
        "id": 17974,
        "status": "FAILED",
        "logstashURL": "http://logstash/00017974.log"
    }, {
        "id": 17976,
        "status": "SUCCESS",
        "logstashURL": "http://logstash/00017976.log"
    }]
}


class DummyResponse(object):
    def __init__(self, response):
        self.status_code = 200
        self.response = response

    def __len__(self):
        return 1

    def json(self):
        return self.response

    @property
    def content(self):
        return self.response


def download_queue_init_ok(**kwargs):
    return LAST_ID


def download_queue_data(**kwargs):
    return SEARCH_QUEUE


class TestQueueSearch(object):

    # object init
    def test_user_missing(self, captured_log):
        vq = verify.QueueSearch(None, 'foo', 'bar')
        assert 'Missing credentials, skipping' in captured_log.getvalue()
        assert vq.skip is True

    def test_password_missing(self, captured_log):
        vq = verify.QueueSearch(None, 'foo', 'bar')
        assert 'Missing credentials, skipping' in captured_log.getvalue()
        assert vq.skip is True

    def test_url_missing(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', None)
        assert 'The queue url is not configured, skipping' in captured_log.getvalue()
        assert vq.skip is True

    def test_init(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        assert vq.skip is False

    # queue init
    def test_queue_init_ok(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_init_ok
        assert vq.queue_init()
        assert vq.skip is False
        assert vq.last_id == 17975

    def test_queue_init_failed(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = lambda **kwargs: None
        assert vq.queue_init() is False
        assert vq.skip is True
        assert vq.last_id is None
        assert 'Failed to initialize' in captured_log.getvalue()

    # download queue
    def test_download_queue_none(self):
        with patch('requests.get', return_value=DummyResponse(None)):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            response = vq.download_queue()
        assert response is None

    def test_download_queue_data(self):
        with patch('requests.get', return_value=DummyResponse(SEARCH_QUEUE)):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            response = vq.download_queue()
        assert response == SEARCH_QUEUE

    def test_download_queue_failed(self):
        with patch('requests.get', return_value=False):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            response = vq.download_queue()
        assert response is None

    def test_download_queue_exception(self, captured_log):
        with patch('requests.get', side_effect=Exception('TestFail')):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            response = vq.download_queue()
        assert response is None
        assert 'TestFail' in captured_log.getvalue()

    # find job in queue
    def test_job_not_found(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        outcome = vq.find_job(17978, 17975)
        assert vq.last_id == 17977
        assert outcome is None

    def test_job_last_found(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        outcome = vq.find_job(17978, 17976)
        assert vq.last_id == 17977
        assert outcome is None

    def test_job_found(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        outcome = vq.find_job(17977, 17976)
        assert vq.last_id == 17977
        assert outcome is SEARCH_QUEUE['jobs'][0]

    # job log handling
    def test_get_log_failed(self, tmpdir, captured_log):
        log_file = os.path.join(str(tmpdir), 'out.log')
        job = {'logstashURL': 'foo'}
        with patch('requests.get', return_value=None):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            vq.get_log(job, log_file)
        assert not os.path.exists(log_file)
        assert 'Failed to download log file' in captured_log.getvalue()

    def test_get_log_saved(self, tmpdir):
        log_file = os.path.join(str(tmpdir), 'out.log')
        job = {'logstashURL': 'foo'}
        with patch('requests.get', return_value=DummyResponse(b'content')):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            vq.get_log(job, log_file)
        assert os.path.exists(log_file)

    def test_get_log_displayed(self, captured_log):
        job = {'logstashURL': 'foo'}
        with patch('requests.get', return_value=None):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            vq.get_log(job)
        assert 'Submit log: foo' in captured_log.getvalue()

    def test_get_log_exception(self, tmpdir, captured_log):
        log_file = os.path.join(str(tmpdir), 'out.log')
        job = {'logstashURL': 'foo'}
        with patch('requests.get', side_effect=Exception('TestFail')):
            vq = verify.QueueSearch('foo', 'bar', 'baz')
            vq.get_log(job, log_file)
        assert not os.path.exists(log_file)
        assert 'TestFail' in captured_log.getvalue()

    # verify submit
    def test_queue_empty_queue(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = lambda **kwargs: None
        vq.last_id = 17975
        outcome = vq.verify_submit(17974, timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert 'not updated' in captured_log.getvalue()

    def test_queue_submit_failed(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        vq.last_id = 17975
        outcome = vq.verify_submit(17974, timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert 'Status = FAILED' in captured_log.getvalue()

    def test_queue_submit_not_found(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        vq.last_id = 17975
        outcome = vq.verify_submit(17978, timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert 'not updated' in captured_log.getvalue()

    def test_queue_submit_found(self, captured_log):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.download_queue = download_queue_data
        vq.last_id = 17975
        outcome = vq.verify_submit(17977, timeout=0.0000001, delay=0.0000001)
        assert outcome
        assert 'successfully updated' in captured_log.getvalue()

    def test_queue_submit_skip(self):
        vq = verify.QueueSearch('foo', 'bar', 'baz')
        vq.skip = True
        outcome = vq.verify_submit(17977, timeout=0.0000001, delay=0.0000001)
        assert outcome is False
