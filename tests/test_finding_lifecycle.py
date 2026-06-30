import pytest

from aotp.finding_candidate import FindingCandidate
from aotp.finding_lifecycle import transition


def test_finding_requires_review_before_confirmation():
    finding = FindingCandidate(
        "id",
        "evidence.json",
        evidence_manifest_sha256="a" * 64,
        verification_reference="verification.json",
        verification_sha256="b" * 64,
        fingerprint="c" * 64,
    )
    transition(finding, "candidate")
    transition(finding, "needs_human_review")
    transition(finding, "confirmed", human_validated=True, reviewer="analyst")
    assert finding.state == "confirmed"
    assert finding.lifecycle_history[-1]["reviewer"] == "analyst"


def test_invalid_transition_is_denied():
    finding = FindingCandidate("id", "evidence.json")
    with pytest.raises(ValueError):
        transition(finding, "paid")
