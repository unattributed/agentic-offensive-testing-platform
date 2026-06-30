"""Service control panel evidence record helpers."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .control_panel import PANEL_SAFE_OBSERVATIONS
from .redaction import assert_redacted, assert_value_redacted

PANEL_EVIDENCE_SCHEMA_VERSION = "1.0"
PANEL_EVIDENCE_FILE = "panel-evidence.json"
PANEL_EVIDENCE_RECORD_TYPE = "service_control_panel_evidence_record"


def _text(value: Any, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def _planned_observation_ids(plan: dict[str, Any]) -> list[str]:
    planned = plan.get("planned_observations", [])
    if not isinstance(planned, list):
        return []
    return [
        item["observation_id"]
        for item in planned
        if isinstance(item, dict)
        and isinstance(item.get("observation_id"), str)
        and item["observation_id"].strip()
    ]


def build_panel_evidence_record(
    case: dict[str, Any],
    *,
    policy_decision: str,
    execution_mode: str,
    tool: str,
    request_count: int,
    response_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Build a redacted local evidence record for safe panel observation planning.

    The record is a deterministic artifact. It describes the planned observation work,
    safety boundaries, and manifest mapping. It does not contain live target material,
    credentials, screenshots, HTTP captures, findings, or report-ready claims.
    """
    plan = response_metadata.get("observation_plan", {})
    if not isinstance(plan, dict):
        plan = {}
    requested_observations = _text_list(case.get("requested_observations"))
    planned_observations = _planned_observation_ids(plan)
    record = {
        "schema_version": PANEL_EVIDENCE_SCHEMA_VERSION,
        "record_type": PANEL_EVIDENCE_RECORD_TYPE,
        "case_id": _text(case.get("id"), "unknown"),
        "module": _text(case.get("module"), "service_control_panel"),
        "category": _text(case.get("category"), "service_control_panel"),
        "target_alias": _text(case.get("target_alias"), "none"),
        "target_category": _text(case.get("target_category"), "placeholder"),
        "panel_alias": _text(case.get("panel_alias"), "none"),
        "panel_type": _text(case.get("panel_type"), "unknown"),
        "policy_decision": policy_decision,
        "execution_mode": execution_mode,
        "tool": tool,
        "request_count": request_count,
        "network_silent": plan.get("network_silent") is True and request_count == 0,
        "safe_observation_only": case.get("safe_observation_only") is True,
        "requested_observations": requested_observations,
        "planned_observations": planned_observations,
        "observation_count": len(planned_observations),
        "supported_observations": sorted(PANEL_SAFE_OBSERVATIONS),
        "observation_plan": plan,
        "credential_material": plan.get("credential_material", "not_collected"),
        "screenshots": plan.get("screenshots", []),
        "captures": plan.get("captures", []),
        "finding_claims": plan.get("finding_claims", []),
        "report_inclusion_status": "excluded_pending_review",
        "redaction_status": "passed",
        "evidence_mappings": _text_list(
            case.get("evidence_mappings") or case.get("artifact_mapping")
        ),
        "safety_boundary": {
            "login_attempts": "not_performed",
            "credential_checks": "not_performed",
            "default_password_checks": "not_performed",
            "crawling": "not_performed",
            "mutation": "not_performed",
            "network_requests": 0,
            "findings": "not_created",
        },
        "no_private_material": (
            "No private scope, target, credential, screenshot, finding, report, "
            "trace, generated capture, campaign memory, or real evidence was committed."
        ),
    }
    validate_panel_evidence_record(record)
    return record


def validate_panel_evidence_record(record: dict[str, Any]) -> None:
    if record.get("schema_version") != PANEL_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("unsupported panel evidence schema version")
    if record.get("record_type") != PANEL_EVIDENCE_RECORD_TYPE:
        raise ValueError("unsupported panel evidence record type")
    required_text = (
        "case_id",
        "module",
        "category",
        "target_alias",
        "panel_alias",
        "panel_type",
        "policy_decision",
        "execution_mode",
        "tool",
        "report_inclusion_status",
        "redaction_status",
    )
    missing = [name for name in required_text if not isinstance(record.get(name), str) or not record[name]]
    if missing:
        raise ValueError("required panel evidence fields are missing: " + ", ".join(missing))
    if record.get("category") != "service_control_panel":
        raise ValueError("panel evidence is only valid for service control panel cases")
    if record.get("execution_mode") not in {"dry_run", "live_stub", "not_executed"}:
        raise ValueError("unsupported panel evidence execution mode")
    if record.get("report_inclusion_status") != "excluded_pending_review":
        raise ValueError("panel evidence records must not be report-ready findings")
    if record.get("redaction_status") != "passed":
        raise ValueError("panel evidence redaction did not pass")
    if record.get("network_silent") is not True:
        raise ValueError("panel evidence must be network silent")
    if record.get("request_count") != 0:
        raise ValueError("panel evidence request_count must be zero")
    if record.get("safe_observation_only") is not True:
        raise ValueError("panel evidence must be safe observation only")
    if record.get("credential_material") != "not_collected":
        raise ValueError("panel evidence must not collect credential material")
    if record.get("screenshots") != []:
        raise ValueError("panel evidence must not include screenshots")
    if record.get("captures") != []:
        raise ValueError("panel evidence must not include captures")
    if record.get("finding_claims") != []:
        raise ValueError("panel evidence must not include finding claims")
    requested = record.get("requested_observations")
    planned = record.get("planned_observations")
    if not isinstance(requested, list) or not requested:
        raise ValueError("panel evidence requested_observations must not be empty")
    if not isinstance(planned, list) or not planned:
        raise ValueError("panel evidence planned_observations must not be empty")
    unsupported = sorted(set(requested) - PANEL_SAFE_OBSERVATIONS)
    if unsupported:
        raise ValueError("panel evidence requested unsupported observations: " + ", ".join(unsupported))
    if planned != requested:
        raise ValueError("panel evidence planned observations must match requested observations")
    boundary = record.get("safety_boundary")
    if not isinstance(boundary, dict) or boundary.get("network_requests") != 0:
        raise ValueError("panel evidence safety boundary is invalid")
    encoded = json.dumps(record, sort_keys=True)
    assert_redacted(encoded)
    assert_value_redacted(record)


def write_panel_evidence_record(
    case: dict[str, Any],
    evidence_directory: str | Path,
    *,
    policy_decision: str,
    execution_mode: str,
    tool: str,
    request_count: int,
    response_metadata: dict[str, Any],
) -> Path:
    record = build_panel_evidence_record(
        case,
        policy_decision=policy_decision,
        execution_mode=execution_mode,
        tool=tool,
        request_count=request_count,
        response_metadata=response_metadata,
    )
    output = Path(evidence_directory)
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    path = output / PANEL_EVIDENCE_FILE
    descriptor, temporary_name = tempfile.mkstemp(prefix=".panel-evidence.", suffix=".tmp", dir=output)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path
