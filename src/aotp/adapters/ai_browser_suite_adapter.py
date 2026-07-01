"""External browser-suite evidence and license boundary contract."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapter_contract import AdapterContract
from ..external_evidence import validate_external_evidence_reference

SAFE_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
ALLOWED_ARTIFACT_CLASSES = frozenset(
    {
        "artifact_manifest",
        "browser_context",
        "dom_snapshot",
        "frame_tree",
        "proxy_capture",
        "rendered_text",
        "screenshot",
    }
)
SOURCE_LICENSE = "AGPL-3.0-or-later"

CONTRACT = AdapterContract(
    adapter_id="browser-suite",
    display_name="browser-suite external evidence contract",
    source_reference="https://github.com/unattributed/ai-browser-security-test-suite",
    supported_capabilities=(
        "evidence_class_mapping",
        "external_browser_evidence_reference",
    ),
    required_approvals=(
        "explicit_private_scope",
        "policy_gate_approval",
        "external_reference_review",
        "license_obligation_review",
    ),
    required_scope_fields=(
        "artifact_class",
        "evidence_alias",
        "relative_path",
        "sha256",
        "provenance",
        "source_commit_alias",
    ),
    required_evidence_handling=(
        "redaction_required",
        "artifact_hash_required",
        "no_implicit_live_run",
        "no_vendored_code",
        "separate_license_obligations_documented",
    ),
    denied_actions=(
        "dependency_import",
        "generated_evidence_commitment",
        "implicit_live_execution",
        "license_boundary_blending",
        "process_invocation",
        "unredacted_model_input",
        "vendored_code",
    ),
    default_execution_mode="external_reference_only",
    live_readiness_status="external_reference_only",
    optional_dependency_status="not_a_dependency",
    provenance_requirements=(
        "source_project",
        "source_commit_alias",
        "artifact_class",
        "sha256",
        "redaction_status",
        "license_review_reference",
    ),
)

CAPABILITIES = {
    "supports": list(CONTRACT.supported_capabilities),
    "requires": list(CONTRACT.required_scope_fields + CONTRACT.required_approvals),
    "denies": list(CONTRACT.denied_actions),
}


def validate_browser_suite_bridge(
    bridge: dict[str, Any],
    evidence_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(bridge, dict) or set(bridge) != {
        "artifact_class",
        "source_commit_alias",
        "license_review_reference",
        "evidence_reference",
    }:
        raise ValueError(
            "browser-suite bridge requires only artifact class, source alias, license review, and evidence reference"
        )
    artifact_class = bridge.get("artifact_class")
    source_commit_alias = bridge.get("source_commit_alias")
    license_review_reference = bridge.get("license_review_reference")
    if artifact_class not in ALLOWED_ARTIFACT_CLASSES:
        raise ValueError("browser-suite artifact class is not approved")
    if (
        not isinstance(source_commit_alias, str)
        or SAFE_ALIAS.fullmatch(source_commit_alias) is None
        or not isinstance(license_review_reference, str)
        or SAFE_ALIAS.fullmatch(license_review_reference) is None
    ):
        raise ValueError("browser-suite provenance aliases must be safe identifiers")
    reference = validate_external_evidence_reference(
        bridge.get("evidence_reference"),
        evidence_root,
    )
    if reference["source_project_or_adapter_contract"] != "browser-suite":
        raise ValueError("browser-suite evidence source must be the browser-suite contract")
    return {
        "adapter_id": CONTRACT.adapter_id,
        "artifact_class": artifact_class,
        "source_commit_alias": source_commit_alias,
        "license_review_reference": license_review_reference,
        "source_license": SOURCE_LICENSE,
        "license_obligations": "separate_review_required",
        "evidence_reference": reference,
        "execution_mode": CONTRACT.default_execution_mode,
        "network_silent": True,
        "request_count": 0,
        "code_imported": False,
        "process_invoked": False,
    }
