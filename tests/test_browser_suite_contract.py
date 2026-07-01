from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from aotp.adapters.ai_browser_suite_adapter import (
    ALLOWED_ARTIFACT_CLASSES,
    CONTRACT,
    SOURCE_LICENSE,
    validate_browser_suite_bridge,
)
from aotp.capability_registry import get_adapter


def _bridge():
    return {
        "artifact_class": "dom_snapshot",
        "source_commit_alias": "reviewed-commit-placeholder",
        "license_review_reference": "license-review-placeholder",
        "evidence_reference": {
            "alias": "browser-evidence-placeholder",
            "relative_path": "browser/dom-placeholder.json",
            "sha256": "b" * 64,
            "provenance": "reviewed local external reference",
            "source_project_or_adapter_contract": "browser-suite",
            "redaction_status": "placeholder_only",
        },
    }


def test_browser_suite_contract_is_external_and_license_separated():
    assert CONTRACT.default_execution_mode == "external_reference_only"
    assert CONTRACT.live_execution_enabled is False
    assert CONTRACT.optional_dependency_status == "not_a_dependency"
    assert "license_obligation_review" in CONTRACT.required_approvals
    assert "separate_license_obligations_documented" in CONTRACT.required_evidence_handling
    assert {"vendored_code", "dependency_import", "license_boundary_blending"}.issubset(
        CONTRACT.denied_actions
    )


def test_browser_suite_bridge_records_license_and_reference_only(tmp_path):
    result = validate_browser_suite_bridge(_bridge(), tmp_path)
    assert result["source_license"] == SOURCE_LICENSE == "AGPL-3.0-or-later"
    assert result["license_obligations"] == "separate_review_required"
    assert result["network_silent"] is True
    assert result["request_count"] == 0
    assert result["code_imported"] is False
    assert result["process_invoked"] is False


def test_browser_suite_bridge_rejects_unknown_artifact_or_source(tmp_path):
    unknown = _bridge()
    unknown["artifact_class"] = "credential_archive"
    with pytest.raises(ValueError, match="artifact class"):
        validate_browser_suite_bridge(unknown, tmp_path)

    wrong_source = deepcopy(_bridge())
    wrong_source["evidence_reference"]["source_project_or_adapter_contract"] = "other"
    with pytest.raises(ValueError, match="source"):
        validate_browser_suite_bridge(wrong_source, tmp_path)


def test_browser_suite_artifact_classes_are_metadata_categories():
    assert ALLOWED_ARTIFACT_CLASSES == {
        "artifact_manifest",
        "browser_context",
        "dom_snapshot",
        "frame_tree",
        "proxy_capture",
        "rendered_text",
        "screenshot",
    }


def test_browser_suite_registry_entry_is_derived_from_validated_contract():
    assert get_adapter("browser-suite") == CONTRACT.as_dict()


@pytest.mark.parametrize(
    "change",
    [
        {"network_silent_default": False},
        {"live_execution_enabled": True},
        {"default_request_budget": 1},
        {"required_approvals": ("license_obligation_review",)},
    ],
)
def test_browser_suite_contract_cannot_enable_integration_execution(change):
    with pytest.raises(ValueError):
        replace(CONTRACT, **change)
