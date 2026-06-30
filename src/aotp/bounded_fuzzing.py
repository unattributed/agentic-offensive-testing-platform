"""Bounded fuzzing authorization and safety constants."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


FUZZING_SUPPORTED_ACTIONS = frozenset(
    {
        "active_fuzzing",
        "plan_bounded_fuzzing",
    }
)

FUZZING_UNSAFE_ACTIONS = frozenset(
    {
        "authentication_abuse",
        "destructive_fuzzing",
        "high_volume_fuzzing",
        "kyc_workflow_fuzzing",
        "payment_workflow_fuzzing",
        "recovery_workflow_fuzzing",
        "support_workflow_fuzzing",
    }
)

FUZZING_SAFE_PAYLOAD_CLASSES = frozenset(
    {
        "boundary_value",
        "empty_value",
        "encoded_literal",
        "format_literal",
        "type_variation",
    }
)

FUZZING_STOP_SIGNALS = frozenset(
    {
        "authentication_lockout_risk",
        "response_size_limit",
        "retry_limit",
        "runtime_limit",
        "target_instability",
    }
)

FUZZING_CORPUS_SCHEMA_VERSION = "1.0"


@dataclass
class FuzzingRequestBudget:
    total_limit: int
    per_endpoint_limit: int
    total_requests: int = 0
    endpoint_requests: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _positive_int(self.total_limit):
            raise ValueError("fuzzing total request limit must be positive")
        if not _positive_int(self.per_endpoint_limit):
            raise ValueError("fuzzing per-endpoint request limit must be positive")
        if self.per_endpoint_limit > self.total_limit:
            raise ValueError("fuzzing per-endpoint limit cannot exceed total limit")

    def reserve(self, endpoint_alias: str, count: int = 1) -> None:
        if not endpoint_alias.strip():
            raise ValueError("fuzzing endpoint alias is missing")
        if not _positive_int(count):
            raise ValueError("fuzzing request count must be positive")
        current = self.endpoint_requests.get(endpoint_alias, 0)
        if current + count > self.per_endpoint_limit:
            raise ValueError("fuzzing per-endpoint request limit exceeded")
        if self.total_requests + count > self.total_limit:
            raise ValueError("fuzzing total request limit exceeded")
        self.endpoint_requests[endpoint_alias] = current + count
        self.total_requests += count


def collect_fuzzing_actions(objective: dict[str, Any]) -> tuple[str, ...]:
    """Return normalized fuzzing actions requested by an objective."""
    actions: list[str] = []
    for field in ("action", "requested_actions"):
        value = objective.get(field)
        if isinstance(value, str) and value.strip():
            actions.append(value.strip())
        elif isinstance(value, list):
            actions.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )
    return tuple(dict.fromkeys(actions))


def collect_fuzzing_stop_signals(objective: dict[str, Any]) -> tuple[str, ...]:
    value = objective.get("detected_stop_signals", [])
    if not isinstance(value, list):
        return ()
    return tuple(
        dict.fromkeys(
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )
    )


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_corpus_reference(reference: Any) -> dict[str, Any]:
    if not isinstance(reference, dict):
        raise ValueError("fuzzing corpus reference must be a mapping")
    expected = {
        "schema_version",
        "alias",
        "sha256",
        "size_bytes",
        "payload_count",
        "payload_class",
        "source",
    }
    if set(reference) != expected:
        raise ValueError("fuzzing corpus reference fields are invalid")
    if reference.get("schema_version") != FUZZING_CORPUS_SCHEMA_VERSION:
        raise ValueError("unsupported fuzzing corpus reference schema")
    for field in ("alias", "payload_class", "source"):
        if not isinstance(reference.get(field), str) or not reference[field].strip():
            raise ValueError(f"fuzzing corpus reference {field} is missing")
    digest = reference.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise ValueError("fuzzing corpus reference SHA256 is invalid")
    if not _non_negative_int(reference.get("size_bytes")):
        raise ValueError("fuzzing corpus reference size_bytes is invalid")
    if not _positive_int(reference.get("payload_count")):
        raise ValueError("fuzzing corpus reference payload_count is invalid")
    if reference["payload_class"] not in FUZZING_SAFE_PAYLOAD_CLASSES:
        raise ValueError("fuzzing corpus reference payload_class is unsafe")
    if reference["source"] != "external_private_corpus":
        raise ValueError("fuzzing corpus reference source is invalid")
    return reference


def build_corpus_reference(
    corpus_path: str | Path,
    *,
    alias: str,
    payload_class: str,
) -> dict[str, Any]:
    path = Path(corpus_path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("fuzzing corpus must be a regular non-symlink file")
    if not alias.strip():
        raise ValueError("fuzzing corpus alias is missing")
    if payload_class not in FUZZING_SAFE_PAYLOAD_CLASSES:
        raise ValueError("fuzzing corpus payload_class is unsafe")
    digest = hashlib.sha256()
    payload_count = 0
    size_bytes = 0
    with path.open("rb") as handle:
        for line in handle:
            digest.update(line)
            size_bytes += len(line)
            if line.strip():
                payload_count += 1
    reference = {
        "schema_version": FUZZING_CORPUS_SCHEMA_VERSION,
        "alias": alias.strip(),
        "sha256": digest.hexdigest(),
        "size_bytes": size_bytes,
        "payload_count": payload_count,
        "payload_class": payload_class,
        "source": "external_private_corpus",
    }
    return validate_corpus_reference(reference)


def write_corpus_reference(reference: dict[str, Any], path: str | Path) -> Path:
    validate_corpus_reference(reference)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".fuzzing-corpus.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(reference, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def fuzzing_boundary_errors(
    objective: dict[str, Any],
    scope: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    payload_classes = objective.get("payload_classes")
    if not isinstance(payload_classes, list) or not payload_classes:
        errors.append("fuzzing payload_classes must not be empty")
        payload_classes = []
    elif any(not isinstance(item, str) or not item.strip() for item in payload_classes):
        errors.append("fuzzing payload_classes must contain non-empty text")
        payload_classes = []
    unsupported_classes = sorted(set(payload_classes) - FUZZING_SAFE_PAYLOAD_CLASSES)
    if unsupported_classes:
        errors.append(
            "fuzzing payload class is not approved as safe: "
            + ", ".join(unsupported_classes)
        )
    unapproved_classes = sorted(
        set(payload_classes) - set(scope.get("safe_payload_classes", []))
    )
    if unapproved_classes:
        errors.append(
            "fuzzing payload class is not explicitly approved by scope: "
            + ", ".join(unapproved_classes)
        )

    payload_count = objective.get("payload_count")
    if not _positive_int(payload_count):
        errors.append("fuzzing payload_count must be a positive integer")
    elif payload_count > scope.get("payload_budget", 0):
        errors.append("fuzzing payload_count exceeds scope payload_budget")
    elif len(set(payload_classes)) > payload_count:
        errors.append("fuzzing payload_count is smaller than the payload class count")

    endpoint_budgets = objective.get("endpoint_request_budgets")
    if not isinstance(endpoint_budgets, dict) or not endpoint_budgets:
        errors.append("fuzzing endpoint_request_budgets must not be empty")
        endpoint_budgets = {}
    invalid_endpoints = [
        str(alias)
        for alias, count in endpoint_budgets.items()
        if not isinstance(alias, str) or not alias.strip() or not _positive_int(count)
    ]
    if invalid_endpoints:
        errors.append("fuzzing endpoint request budgets are invalid")
    per_endpoint_limit = scope.get("per_endpoint_limit", 0)
    exceeded_endpoints = sorted(
        str(alias)
        for alias, count in endpoint_budgets.items()
        if _positive_int(count) and count > per_endpoint_limit
    )
    if exceeded_endpoints:
        errors.append(
            "fuzzing endpoint budget exceeds per_endpoint_limit: "
            + ", ".join(exceeded_endpoints)
        )
    planned_requests = sum(
        count for count in endpoint_budgets.values() if _positive_int(count)
    )
    if planned_requests > scope.get("request_budget", 0):
        errors.append("fuzzing planned requests exceed scope request_budget")

    for field in ("max_response_bytes", "max_runtime_seconds"):
        value = objective.get(field)
        if not _positive_int(value):
            errors.append(f"fuzzing {field} must be a positive integer")
        elif value > scope.get(field, 0):
            errors.append(f"fuzzing {field} exceeds scope limit")
    retries = objective.get("max_retries")
    if not _non_negative_int(retries):
        errors.append("fuzzing max_retries must be a non-negative integer")
    elif retries > scope.get("max_retries", -1):
        errors.append("fuzzing max_retries exceeds scope limit")

    reference = objective.get("corpus_reference")
    if reference is not None:
        try:
            validated_reference = validate_corpus_reference(reference)
            if validated_reference["payload_count"] > scope.get("payload_budget", 0):
                errors.append("fuzzing corpus payload_count exceeds scope payload_budget")
            if (
                _positive_int(payload_count)
                and validated_reference["payload_count"] > payload_count
            ):
                errors.append("fuzzing corpus payload_count exceeds objective payload_count")
            if validated_reference["payload_class"] not in set(payload_classes):
                errors.append("fuzzing corpus payload_class is not requested")
        except ValueError as exc:
            errors.append(str(exc))

    stop_signals = collect_fuzzing_stop_signals(objective)
    unsupported_signals = sorted(set(stop_signals) - FUZZING_STOP_SIGNALS)
    if unsupported_signals:
        errors.append(
            "fuzzing stop signal is unsupported: " + ", ".join(unsupported_signals)
        )
    return tuple(dict.fromkeys(errors))


def build_fuzzing_dry_run_plan(objective: dict[str, Any]) -> dict[str, Any]:
    endpoint_budgets = objective.get("endpoint_request_budgets")
    if not isinstance(endpoint_budgets, dict) or not endpoint_budgets:
        raise ValueError("fuzzing endpoint_request_budgets must not be empty")
    if any(
        not isinstance(alias, str)
        or not alias.strip()
        or not _positive_int(count)
        for alias, count in endpoint_budgets.items()
    ):
        raise ValueError("fuzzing endpoint request budgets are invalid")
    payload_classes = objective.get("payload_classes")
    if not isinstance(payload_classes, list) or not payload_classes:
        raise ValueError("fuzzing payload_classes must not be empty")
    unsupported_classes = sorted(set(payload_classes) - FUZZING_SAFE_PAYLOAD_CLASSES)
    if unsupported_classes:
        raise ValueError(
            "fuzzing payload class is not approved as safe: "
            + ", ".join(unsupported_classes)
        )
    payload_count = objective.get("payload_count")
    if not _positive_int(payload_count):
        raise ValueError("fuzzing payload_count must be a positive integer")
    if len(set(payload_classes)) > payload_count:
        raise ValueError("fuzzing payload_count is smaller than the payload class count")
    for field in ("max_response_bytes", "max_runtime_seconds"):
        if not _positive_int(objective.get(field)):
            raise ValueError(f"fuzzing {field} must be a positive integer")
    if not _non_negative_int(objective.get("max_retries")):
        raise ValueError("fuzzing max_retries must be a non-negative integer")
    corpus_reference = objective.get("corpus_reference")
    if corpus_reference is not None:
        validate_corpus_reference(corpus_reference)
    stop_signals = collect_fuzzing_stop_signals(objective)
    unsupported_signals = sorted(set(stop_signals) - FUZZING_STOP_SIGNALS)
    if unsupported_signals:
        raise ValueError(
            "fuzzing stop signal is unsupported: " + ", ".join(unsupported_signals)
        )
    if stop_signals:
        raise ValueError(
            "fuzzing stop condition detected: " + ", ".join(sorted(stop_signals))
        )
    return {
        "target_alias": str(objective.get("target_alias", "")),
        "api": str(objective.get("api", "")),
        "payload_classes": list(payload_classes),
        "payload_count": payload_count,
        "endpoint_request_budgets": dict(sorted(endpoint_budgets.items())),
        "planned_request_count": sum(endpoint_budgets.values()),
        "max_response_bytes": objective.get("max_response_bytes"),
        "max_retries": objective.get("max_retries"),
        "max_runtime_seconds": objective.get("max_runtime_seconds"),
        "corpus_reference": corpus_reference,
        "detected_stop_signals": list(stop_signals),
        "execution": "not_executed",
        "network_silent": True,
        "request_count": 0,
        "payload_values": "not_recorded",
    }
