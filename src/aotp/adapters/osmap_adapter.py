"""Clean-room OSMAP external evidence bridge contract."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..adapter_contract import AdapterContract
from ..external_evidence import validate_external_evidence_reference

SAFE_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")

CONTRACT = AdapterContract(
    adapter_id="osmap",
    display_name="OSMAP external local evidence contract",
    source_reference="https://github.com/unattributed/OSMAP",
    supported_capabilities=(
        "explicit_case_alias_bridge",
        "external_local_evidence_reference",
        "wstg_mapping_provenance",
    ),
    required_approvals=(
        "explicit_private_scope",
        "policy_gate_approval",
        "external_reference_review",
    ),
    required_scope_fields=(
        "case_alias",
        "evidence_alias",
        "relative_path",
        "sha256",
        "provenance",
        "source_commit_alias",
    ),
    required_evidence_handling=(
        "redaction_required",
        "artifact_hash_required",
        "clean_room_mapping_only",
        "no_implicit_live_run",
        "no_vendored_code",
    ),
    denied_actions=(
        "dependency_import",
        "generated_evidence_commitment",
        "implicit_live_execution",
        "process_invocation",
        "secret_export",
        "vendored_code",
    ),
    default_execution_mode="external_reference_only",
    live_readiness_status="external_reference_only",
    optional_dependency_status="not_a_dependency",
    provenance_requirements=(
        "source_project",
        "source_commit_alias",
        "case_alias",
        "sha256",
        "redaction_status",
    ),
)

CAPABILITIES = {
    "supports": list(CONTRACT.supported_capabilities),
    "requires": list(CONTRACT.required_scope_fields + CONTRACT.required_approvals),
    "denies": list(CONTRACT.denied_actions),
}


def validate_osmap_bridge(
    bridge: dict[str, Any],
    evidence_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(bridge, dict) or set(bridge) != {
        "case_alias",
        "source_commit_alias",
        "evidence_reference",
    }:
        raise ValueError(
            "OSMAP bridge requires only case_alias, source_commit_alias, and evidence_reference"
        )
    case_alias = bridge.get("case_alias")
    source_commit_alias = bridge.get("source_commit_alias")
    if (
        not isinstance(case_alias, str)
        or SAFE_ALIAS.fullmatch(case_alias) is None
        or not isinstance(source_commit_alias, str)
        or SAFE_ALIAS.fullmatch(source_commit_alias) is None
    ):
        raise ValueError("OSMAP bridge aliases must be safe non-sensitive identifiers")
    reference = validate_external_evidence_reference(
        bridge.get("evidence_reference"),
        evidence_root,
    )
    if reference["source_project_or_adapter_contract"] != "osmap":
        raise ValueError("OSMAP bridge evidence source must be the osmap contract")
    return {
        "adapter_id": CONTRACT.adapter_id,
        "case_alias": case_alias,
        "source_commit_alias": source_commit_alias,
        "evidence_reference": reference,
        "execution_mode": CONTRACT.default_execution_mode,
        "network_silent": True,
        "request_count": 0,
        "code_imported": False,
        "process_invoked": False,
    }
