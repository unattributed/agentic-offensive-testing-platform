from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from aotp.adapters.osmap_adapter import CONTRACT, validate_osmap_bridge
from aotp.capability_registry import get_adapter


def _bridge():
    return {
        "case_alias": "mailbox-case-placeholder",
        "source_commit_alias": "reviewed-commit-placeholder",
        "evidence_reference": {
            "alias": "osmap-evidence-placeholder",
            "relative_path": "osmap/evidence-placeholder.json",
            "sha256": "a" * 64,
            "provenance": "reviewed local external reference",
            "source_project_or_adapter_contract": "osmap",
            "redaction_status": "placeholder_only",
        },
    }


def test_osmap_contract_is_external_reference_only():
    assert CONTRACT.default_execution_mode == "external_reference_only"
    assert CONTRACT.live_execution_enabled is False
    assert CONTRACT.default_request_budget == 0
    assert CONTRACT.optional_dependency_status == "not_a_dependency"
    assert {"no_vendored_code", "no_implicit_live_run"}.issubset(
        CONTRACT.required_evidence_handling
    )
    assert {"vendored_code", "process_invocation", "dependency_import"}.issubset(
        CONTRACT.denied_actions
    )


def test_osmap_bridge_returns_only_reference_metadata(tmp_path):
    result = validate_osmap_bridge(_bridge(), tmp_path)
    assert result["execution_mode"] == "external_reference_only"
    assert result["network_silent"] is True
    assert result["request_count"] == 0
    assert result["code_imported"] is False
    assert result["process_invoked"] is False


def test_osmap_bridge_rejects_wrong_source_or_escaped_path(tmp_path):
    wrong_source = _bridge()
    wrong_source["evidence_reference"]["source_project_or_adapter_contract"] = "other"
    with pytest.raises(ValueError, match="source"):
        validate_osmap_bridge(wrong_source, tmp_path)

    escaped = _bridge()
    escaped["evidence_reference"]["relative_path"] = "../outside.json"
    with pytest.raises(ValueError, match="must not escape"):
        validate_osmap_bridge(escaped, tmp_path)


def test_osmap_bridge_rejects_unknown_fields_and_unsafe_alias(tmp_path):
    expanded = _bridge() | {"execute": True}
    with pytest.raises(ValueError, match="requires only"):
        validate_osmap_bridge(expanded, tmp_path)

    unsafe = deepcopy(_bridge())
    unsafe["case_alias"] = "https://target.invalid/case"
    with pytest.raises(ValueError, match="safe"):
        validate_osmap_bridge(unsafe, tmp_path)


def test_osmap_registry_entry_is_derived_from_validated_contract():
    assert get_adapter("osmap") == CONTRACT.as_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"network_silent_default": False},
        {"live_execution_enabled": True},
        {"default_request_budget": 1},
        {"required_approvals": ("external_reference_review",)},
    ],
)
def test_osmap_contract_cannot_enable_integration_execution(change):
    with pytest.raises(ValueError):
        replace(CONTRACT, **change)
