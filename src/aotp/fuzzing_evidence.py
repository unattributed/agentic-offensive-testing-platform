"""Evidence records for network-silent bounded fuzzing plans."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .bounded_fuzzing import FUZZING_SAFE_PAYLOAD_CLASSES, validate_corpus_reference
from .redaction import assert_redacted, assert_value_redacted


FUZZING_EVIDENCE_SCHEMA_VERSION = "1.0"
FUZZING_EVIDENCE_FILE = "fuzzing-evidence.json"
FUZZING_EVIDENCE_RECORD_TYPE = "bounded_fuzzing_evidence_record"


def build_fuzzing_evidence_record(
    case: dict[str, Any],
    *,
    policy_decision: str,
    execution_mode: str,
    tool: str,
    request_count: int,
    response_metadata: dict[str, Any],
) -> dict[str, Any]:
    plan = response_metadata.get("fuzzing_plan")
    if not isinstance(plan, dict):
        raise ValueError("fuzzing evidence requires a dry-run plan")
    record = {
        "schema_version": FUZZING_EVIDENCE_SCHEMA_VERSION,
        "record_type": FUZZING_EVIDENCE_RECORD_TYPE,
        "case_id": str(case.get("id", "")).strip(),
        "module": str(case.get("module", "")).strip(),
        "target_alias": str(case.get("target_alias", "")).strip(),
        "api": str(case.get("api", "")).strip(),
        "policy_decision": policy_decision,
        "execution_mode": execution_mode,
        "tool": tool,
        "request_count": request_count,
        "network_silent": plan.get("network_silent") is True and request_count == 0,
        "payload_classes": plan.get("payload_classes"),
        "payload_count": plan.get("payload_count"),
        "endpoint_request_budgets": plan.get("endpoint_request_budgets"),
        "planned_request_count": plan.get("planned_request_count"),
        "max_response_bytes": plan.get("max_response_bytes"),
        "max_retries": plan.get("max_retries"),
        "max_runtime_seconds": plan.get("max_runtime_seconds"),
        "corpus_reference": plan.get("corpus_reference"),
        "detected_stop_signals": plan.get("detected_stop_signals"),
        "payload_values": "not_recorded",
        "report_inclusion_status": "excluded_pending_review",
        "redaction_status": "passed",
    }
    validate_fuzzing_evidence_record(record)
    return record


def validate_fuzzing_evidence_record(record: dict[str, Any]) -> None:
    if record.get("schema_version") != FUZZING_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("unsupported fuzzing evidence schema")
    if record.get("record_type") != FUZZING_EVIDENCE_RECORD_TYPE:
        raise ValueError("unsupported fuzzing evidence record type")
    for field in (
        "case_id",
        "module",
        "target_alias",
        "api",
        "policy_decision",
        "execution_mode",
        "tool",
    ):
        if not isinstance(record.get(field), str) or not record[field]:
            raise ValueError(f"fuzzing evidence {field} is missing")
    if record["module"] != "bounded_fuzzing":
        raise ValueError("fuzzing evidence module is invalid")
    if record.get("network_silent") is not True or record.get("request_count") != 0:
        raise ValueError("fuzzing evidence must be network silent")
    if record.get("payload_values") != "not_recorded":
        raise ValueError("fuzzing evidence must not contain payload values")
    if record.get("report_inclusion_status") != "excluded_pending_review":
        raise ValueError("fuzzing evidence must remain excluded pending review")
    if record.get("redaction_status") != "passed":
        raise ValueError("fuzzing evidence redaction did not pass")
    if not isinstance(record.get("payload_classes"), list) or not record["payload_classes"]:
        raise ValueError("fuzzing evidence payload_classes are invalid")
    if set(record["payload_classes"]) - FUZZING_SAFE_PAYLOAD_CLASSES:
        raise ValueError("fuzzing evidence contains unsafe payload classes")
    if not isinstance(record.get("payload_count"), int) or record["payload_count"] <= 0:
        raise ValueError("fuzzing evidence payload_count is invalid")
    endpoint_budgets = record.get("endpoint_request_budgets")
    if not isinstance(endpoint_budgets, dict) or not endpoint_budgets:
        raise ValueError("fuzzing evidence endpoint budgets are invalid")
    if any(
        not isinstance(alias, str)
        or not alias
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count <= 0
        for alias, count in endpoint_budgets.items()
    ):
        raise ValueError("fuzzing evidence endpoint budgets are invalid")
    if record.get("planned_request_count") != sum(endpoint_budgets.values()):
        raise ValueError("fuzzing evidence request count mapping is invalid")
    for field in ("max_response_bytes", "max_runtime_seconds"):
        if not isinstance(record.get(field), int) or record[field] <= 0:
            raise ValueError(f"fuzzing evidence {field} is invalid")
    if not isinstance(record.get("max_retries"), int) or record["max_retries"] < 0:
        raise ValueError("fuzzing evidence max_retries is invalid")
    if record.get("detected_stop_signals") != []:
        raise ValueError("executed fuzzing plans must not contain stop signals")
    reference = record.get("corpus_reference")
    if reference is not None:
        validate_corpus_reference(reference)
    encoded = json.dumps(record, sort_keys=True)
    assert_redacted(encoded)
    assert_value_redacted(record)


def write_fuzzing_evidence_record(
    case: dict[str, Any],
    evidence_directory: str | Path,
    *,
    policy_decision: str,
    execution_mode: str,
    tool: str,
    request_count: int,
    response_metadata: dict[str, Any],
) -> Path:
    record = build_fuzzing_evidence_record(
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
    path = output / FUZZING_EVIDENCE_FILE
    descriptor, temporary_name = tempfile.mkstemp(prefix=".fuzzing-evidence.", dir=output)
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
