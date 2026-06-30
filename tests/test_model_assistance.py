from __future__ import annotations

import pytest

from aotp.verifier import (
    REPORT_ASSISTANCE_SCHEMA,
    VERIFICATION_ASSISTANCE_SCHEMA,
    parse_report_assistance,
    parse_verification_assistance,
    prepare_model_evidence_summaries,
    request_report_assistance,
    request_verification_assistance,
)


class StubAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, task, payload, schema):
        self.calls.append((task, payload, schema))
        return self.result


def _summaries():
    return [
        {
            "evidence_reference": "manifest:sha256:example",
            "summary": "Recorded metadata indicates the configured control is present.",
        }
    ]


def test_verification_assistance_receives_only_evidence_summaries():
    adapter = StubAdapter(
        {
            "evidence_summary": "The provided record states the control is present.",
            "evidence_references": ["manifest:sha256:example"],
            "uncertainty": "The record does not prove runtime enforcement.",
        }
    )
    result = request_verification_assistance(adapter, _summaries())
    assert result.evidence_references == ("manifest:sha256:example",)
    _task, payload, schema = adapter.calls[0]
    assert payload == {"evidence_summaries": _summaries()}
    assert schema == VERIFICATION_ASSISTANCE_SCHEMA


@pytest.mark.parametrize("field", ["authorization", "verdict", "confidence", "policy"])
def test_verification_assistance_cannot_set_authority_or_verdict(field):
    result = {
        "evidence_summary": "Summary.",
        "evidence_references": ["evidence-a"],
        "uncertainty": "Unknown.",
        field: True,
    }
    with pytest.raises(ValueError, match="cannot set"):
        parse_verification_assistance(result, {"evidence-a"})


def test_verification_assistance_rejects_unknown_evidence():
    with pytest.raises(ValueError, match="unknown evidence"):
        parse_verification_assistance(
            {
                "evidence_summary": "Summary.",
                "evidence_references": ["invented-evidence"],
                "uncertainty": "Unknown.",
            },
            {"evidence-a"},
        )


@pytest.mark.parametrize("field", ["raw_manifest", "authorization", "target", "secret"])
def test_model_input_rejects_non_summary_fields(field):
    item = _summaries()[0] | {field: "not allowed"}
    with pytest.raises(ValueError, match="only evidence_reference and summary"):
        prepare_model_evidence_summaries([item])


def test_report_assistance_is_evidence_bound_and_advisory():
    adapter = StubAdapter(
        {
            "title": "Observed control metadata",
            "draft_summary": "The provided record describes the control.",
            "evidence_references": ["manifest:sha256:example"],
            "caveat": "Runtime effectiveness was not established.",
        }
    )
    result = request_report_assistance(adapter, _summaries())
    assert result.caveat == "Runtime effectiveness was not established."
    assert adapter.calls[0][2] == REPORT_ASSISTANCE_SCHEMA


@pytest.mark.parametrize("field", ["severity", "authorization", "impact", "policy"])
def test_report_assistance_cannot_set_authority_or_findings(field):
    result = {
        "title": "Title",
        "draft_summary": "Summary",
        "evidence_references": ["evidence-a"],
        "caveat": "Caveat",
        field: "not allowed",
    }
    with pytest.raises(ValueError, match="cannot set"):
        parse_report_assistance(result, {"evidence-a"})
