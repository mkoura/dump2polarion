# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring,no-self-use,too-few-public-methods,protected-access


from __future__ import unicode_literals

import os

from mock import patch

from dump2polarion import submit, utils
from tests import conf


# pylint: disable=unused-argument
class DummySession(object):
    def __init__(self, method):
        self._method = method

    def get(self, *args, **kwargs):
        return self._method()

    def post(self, *args, **kwargs):
        return self._method()


class DummyResponse(object):
    def __init__(self, response=None):
        self.status_code = 200
        self.response = response or {}

    def __len__(self):
        return 1

    def json(self):
        return self.response

    @property
    def content(self):
        return self.response


class TestSubmit(object):
    def test_missing_input(self, config_prop, captured_log):
        submit.submit("", config=config_prop)
        assert "no data supplied" in captured_log.getvalue()

    def test_missing_credentials(self, config_prop, captured_log):
        submit.submit("<foo/>", config=config_prop)
        assert "missing credentials" in captured_log.getvalue()

    def test_missing_target(self, config_prop, captured_log):
        submit.submit("<foo/>", config=config_prop, user="john", password="123")
        assert "submit target not found" in captured_log.getvalue()

    def test_missing_testrun_id(self, config_prop, captured_log):
        submit.submit(
            "<testsuites><properties></properties></testsuites>",
            config=config_prop,
            user="john",
            password="123",
            session="foo",
        )
        assert "missing testrun id" in captured_log.getvalue()

    def test_fill_testrun_submit(self, config_prop):
        fname = "properties.xml"
        submit.submit(
            xml_file=os.path.join(conf.DATA_PATH, fname),
            testrun_id="5_8_0_17",
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(DummyResponse),
        )

    def test_get_testcases_taget(self, config_prop):
        xml_root = utils.get_xml_root_from_str("<testcases/>")
        response = submit._get_submit_target(xml_root, config_prop)
        assert "testcase" in response

    def test_get_testsuites_taget(self, config_prop):
        xml_root = utils.get_xml_root_from_str("<testsuites/>")
        response = submit._get_submit_target(xml_root, config_prop)
        assert "xunit" in response

    def test_get_requirements_taget(self, config_prop):
        xml_root = utils.get_xml_root_from_str("<requirements/>")
        response = submit._get_submit_target(xml_root, config_prop)
        assert "requirement" in response

    def test_file_testsuites_failure(self, config_prop, captured_log):
        class Response(object):
            def __init__(self):
                self.status_code = 404

            def __len__(self):
                return 0

        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        response = submit.submit(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(Response),
        )
        assert not response
        assert "HTTP status 404: failed to submit" in captured_log.getvalue()

    def test_file_testsuites_none(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        response = submit.submit(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(lambda: None),
        )
        assert not response
        assert "Failed to submit" in captured_log.getvalue()

    def test_file_testsuites_exception(self, config_prop, captured_log):
        def _raise():
            raise Exception("request failed")

        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        response = submit.submit(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(_raise),
        )
        assert not response
        logged_data = captured_log.getvalue()
        assert "request failed" in logged_data
        assert "Failed to submit" in logged_data

    def test_file_testsuites_success(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        response = submit.submit(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(
                lambda: DummyResponse({"files": {"results.xml": {"job-ids": [1, 2]}}})
            ),
        )
        assert response
        logged_data = captured_log.getvalue()
        assert "Results received" in logged_data
        assert "Job IDs" in logged_data

    def test_file_testcases_success(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "testcases.xml")
        response = submit.submit(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(
                lambda: DummyResponse({"files": {"results.xml": {"job-ids": [1, 2]}}})
            ),
        )
        assert response
        logged_data = captured_log.getvalue()
        assert "Results received" in logged_data
        assert "Job ID" in logged_data


class TestSubmitAndVerify(object):
    def test_missing_input(self, config_prop, captured_log):
        submit.submit_and_verify("", config=config_prop)
        assert "no data supplied" in captured_log.getvalue()

    def test_no_verify(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        response = submit.submit_and_verify(
            xml_file=input_file,
            config=config_prop,
            user="john",
            password="123",
            session=DummySession(
                lambda: DummyResponse({"files": {"results.xml": {"job-ids": [1, 2]}}})
            ),
            no_verify=True,
        )
        assert response
        assert "Results received" in captured_log.getvalue()

    def test_verify_failed(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        with patch("dump2polarion.verify.QueueSearch") as mock:
            instance = mock.return_value
            instance.verify_submit.return_value = False
            response = submit.submit_and_verify(
                xml_file=input_file,
                config=config_prop,
                user="john",
                password="123",
                session=DummySession(
                    lambda: DummyResponse({"files": {"results.xml": {"job-ids": [1, 2]}}})
                ),
            )
        assert not response
        assert "Results received" in captured_log.getvalue()

    def test_verify_success(self, config_prop, captured_log):
        input_file = os.path.join(conf.DATA_PATH, "complete_transform.xml")
        with patch("dump2polarion.verify.QueueSearch") as mock:
            instance = mock.return_value
            instance.verify_submit.return_value = True
            response = submit.submit_and_verify(
                xml_file=input_file,
                config=config_prop,
                user="john",
                password="123",
                session=DummySession(
                    lambda: DummyResponse({"files": {"results.xml": {"job-ids": [1, 2]}}})
                ),
            )
        assert response
        assert "Results received" in captured_log.getvalue()
