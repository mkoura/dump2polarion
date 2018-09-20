# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,no-self-use,unused-argument,invalid-name

from __future__ import unicode_literals

import os

from dump2polarion import verify

SEARCH_QUEUE = {
    "jobsPerPage": 50,
    "maxPages": 2,
    "currentPage": 1,
    "jobs": [
        {"id": 17977, "status": "SUCCESS", "logstashURL": "http://logstash/00017977.log"},
        {"id": 17974, "status": "FAILED", "logstashURL": "http://logstash/00017974.log"},
        {"id": 17976, "status": "SUCCESS", "logstashURL": "http://logstash/00017976.log"},
    ],
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


# pylint: disable=too-few-public-methods
class DummySession(object):
    def __init__(self, get):
        self._get = get

    def get(self, *args, **kwargs):
        return self._get()


def download_queue_data(*args, **kwargs):
    return SEARCH_QUEUE


# pylint: disable=too-many-public-methods
class TestQueueSearch(object):

    # object init
    def test_session_missing(self, captured_log):
        vq = verify.QueueSearch(None, "foo", None)
        assert "Missing requests session, skipping" in captured_log.getvalue()
        assert vq.skip is True

    def test_url_missing(self, captured_log):
        vq = verify.QueueSearch("foo", None, None)
        assert "The queue url is not configured, skipping" in captured_log.getvalue()
        assert vq.skip is True

    def test_init(self):
        vq = verify.QueueSearch("foo", "bar", None)
        assert vq.skip is False

    # download queue
    def test_download_queue_none(self):
        vq = verify.QueueSearch(DummySession(lambda: DummyResponse(None)), "bar", None)
        response = vq.download_queue([1, 2])
        assert response is None

    def test_download_queue_data(self):
        vq = verify.QueueSearch(DummySession(lambda: DummyResponse(SEARCH_QUEUE)), "bar", None)
        response = vq.download_queue([1, 2])
        assert response == SEARCH_QUEUE

    def test_download_queue_failed(self):
        vq = verify.QueueSearch(DummySession(lambda: False), "bar", None)
        response = vq.download_queue([1, 2])
        assert response is None

    def test_download_queue_exception(self, captured_log):
        def _raise():
            raise Exception("TestFail")

        vq = verify.QueueSearch(DummySession(_raise), "bar", None)
        response = vq.download_queue([1, 2])
        assert response is None
        assert "TestFail" in captured_log.getvalue()

    # find job in queue
    def test_job_not_found(self):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.find_jobs([17978, 17975])
        assert outcome == []

    def test_job_found(self):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.find_jobs([17977, 17976])
        assert outcome[0] == SEARCH_QUEUE["jobs"][0]
        assert outcome[1] == SEARCH_QUEUE["jobs"][2]

    # job log handling
    def test_get_log_failed(self, tmpdir, captured_log):
        log_file = os.path.join(str(tmpdir), "out.log")
        jobs = [{"id": "111"}]
        vq = verify.QueueSearch(
            DummySession(lambda: DummyResponse(None)), "bar", "http://example.com"
        )
        vq.get_logs(jobs, log_file)
        assert not os.path.exists(log_file)
        assert "Failed to download log file" in captured_log.getvalue()

    def test_get_log_saved(self, tmpdir):
        log_file = os.path.join(str(tmpdir), "out.log")
        jobs = [{"id": "111"}]
        vq = verify.QueueSearch(
            DummySession(lambda: DummyResponse(b"content")), "bar", "http://example.com"
        )
        vq.get_logs(jobs, log_file)
        assert os.path.exists(log_file)

    def test_get_log_displayed(self, captured_log):
        jobs = [{"id": "111"}]
        vq = verify.QueueSearch(
            DummySession(lambda: DummyResponse(None)), "bar", "http://example.com"
        )
        vq.get_logs(jobs)
        assert "Submit log for job 111: http://example.com?jobId=111" in captured_log.getvalue()

    def test_get_log_exception(self, tmpdir, captured_log):
        def _raise():
            raise Exception("TestFail")

        log_file = os.path.join(str(tmpdir), "out.log")
        jobs = [{"id": "111"}]
        vq = verify.QueueSearch(DummySession(_raise), "bar", "http://example.com")
        vq.get_logs(jobs, log_file)
        assert not os.path.exists(log_file)
        assert "TestFail" in captured_log.getvalue()

    # verify submit
    def test_queue_empty_queue(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = lambda *args: None
        outcome = vq.verify_submit([17974], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert "not updated" in captured_log.getvalue()

    def test_queue_submit_failed_one(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.verify_submit([17974, 17976, 17977], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert "status: FAILED" in captured_log.getvalue()
        assert "Some import jobs failed" in captured_log.getvalue()

    def test_queue_submit_failed_all(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.verify_submit([17974], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert "status: FAILED" in captured_log.getvalue()
        assert "Import failed!" in captured_log.getvalue()

    def test_queue_submit_not_found_one(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.verify_submit([17976, 17978], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert "not updated" in captured_log.getvalue()
        assert "Import failed!" in captured_log.getvalue()

    def test_queue_submit_not_found_all(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.verify_submit([17978], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
        assert "not updated" in captured_log.getvalue()
        assert "Import failed!" in captured_log.getvalue()

    def test_queue_submit_found(self, captured_log):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.download_queue = download_queue_data
        outcome = vq.verify_submit([17976, 17977], timeout=0.0000001, delay=0.0000001)
        assert outcome
        assert "successfully updated" in captured_log.getvalue()

    def test_queue_submit_skip(self):
        vq = verify.QueueSearch("foo", "bar", None)
        vq.skip = True
        outcome = vq.verify_submit([17977], timeout=0.0000001, delay=0.0000001)
        assert outcome is False
