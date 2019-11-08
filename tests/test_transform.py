# pylint: disable=missing-docstring,redefined-outer-name,no-self-use,protected-access,invalid-name

from typing import List, Tuple

import pytest

from dump2polarion.exporters import transform_projects

# format:
# original record, expected record, parameter id

NOT_PASSED = [
    ({"title": "test_1", "verdict": "failed"}, None, "failed_removed"),
    ({"title": "test_1", "verdict": "skipped"}, None, "skipped_nobz"),
    (
        {"title": "test_1", "verdict": "skipped", "comment": "BZ123"},
        {"title": "test_1", "verdict": "skipped", "comment": "BZ123"},
        "skipped_bz",
    ),
    (
        {"title": "test_1", "verdict": "skipped", "comment": "BZ 123"},
        {"title": "test_1", "verdict": "skipped", "comment": "BZ 123"},
        "skipped_bz",
    ),
    (
        {"title": "test_1", "verdict": "skipped", "comment": "SKIPME: foo"},
        {"title": "test_1", "verdict": "skipped", "comment": "foo"},
        "skipped_skipme",
    ),
    (
        {"title": "test_1", "verdict": "failed", "comment": "FAILME: foo"},
        {"title": "test_1", "verdict": "failed", "comment": "foo"},
        "failed_failme",
    ),
    ({"title": "test_1", "verdict": "wait"}, {"title": "test_1", "verdict": "wait"}, "waiting"),
]  # type: List[Tuple]

RHCF3_ONLY = [
    (
        {
            "classname": "cfme.tests.rest.TestRESTAPI",
            "title": "test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        {
            "title": "TestRESTAPI.test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        "append_class",
    ),
    (
        {
            "classname": "TestRESTAPI",
            "title": "test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        {
            "title": "test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        "no_append_class",
    ),
    (
        {
            "classname": "cfme.tests.rest",
            "title": "test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        {
            "title": "test_1",
            "verdict": "passed",
            "comment": "comment",
            "file": "cfme/tests/rest.py",
        },
        "no_append_class",
    ),
    (
        {
            "title": "test_1",
            "verdict": "passed",
            "source": "jenkins",
            "job_name": "downstream",
            "run": "123",
        },
        {
            "title": "test_1",
            "verdict": "passed",
            "comment": "Source: jenkins/downstream/123",
            "source": "jenkins",
            "job_name": "downstream",
            "run": "123",
        },
        "passed_comment",
    ),
]  # type: List[Tuple]

RHCF3_DATA = RHCF3_ONLY + NOT_PASSED


class TestTransform:
    @pytest.fixture(scope="class")
    def config_rhcf3(self):
        return {"polarion-project-id": "RHCF3"}

    @pytest.mark.parametrize("data", RHCF3_DATA, ids=[d[2] for d in RHCF3_DATA])
    def test_transform_rhcf3(self, config_rhcf3, data):
        tfunc = transform_projects.get_xunit_transform(config_rhcf3)
        result = tfunc(data[0])
        assert result == data[1]
