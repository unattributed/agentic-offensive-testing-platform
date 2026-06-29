import pytest

from aotp.finding_candidate import FindingCandidate
from aotp.finding_lifecycle import transition


def test_finding_requires_review_before_confirmation():
    finding = FindingCandidate("id", "evidence.json")
    transition(finding, "candidate")
    transition(finding, "needs_human_review")
    transition(finding, "confirmed", human_validated=True)
    assert finding.state == "confirmed"


def test_invalid_transition_is_denied():
    finding = FindingCandidate("id", "evidence.json")
    with pytest.raises(ValueError):
        transition(finding, "paid")
