import pytest

from aotp.finding_candidate import FindingCandidate


def test_candidate_requires_evidence():
    with pytest.raises(ValueError):
        FindingCandidate("id", "").validate()


def test_severity_confidence_and_evidence_strength_are_separate():
    finding = FindingCandidate("id", "evidence.json", severity_candidate="high", confidence="low", evidence_strength="medium")
    finding.validate()
    assert (finding.severity_candidate, finding.confidence, finding.evidence_strength) == ("high", "low", "medium")
