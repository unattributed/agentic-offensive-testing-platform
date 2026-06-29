"""Verifier verdict contract."""

from enum import StrEnum


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    MANUAL_REVIEW = "manual_review"
    STOPPED_BY_POLICY = "stopped_by_policy"
