"""Allowed values for verdicts."""


class Verdicts:
    """Valid verdicts."""

    PASS = ("passed", "pass")
    FAIL = ("failed", "fail")
    SKIP = ("skipped", "skip", "blocked")
    WAIT = ("null", "wait", "waiting")
