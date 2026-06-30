"""Versioned, integrity-checked campaign state checkpoints."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_SCHEMA_VERSION = "1.0"
CAMPAIGN_STATUSES = {
    "planned",
    "running",
    "paused_for_human_review",
    "ready_to_resume",
    "completed",
    "stopped_by_policy",
    "stopped_by_operator",
    "stopped_by_budget",
    "stopped_by_condition",
    "failed",
}


@dataclass
class CampaignEvent:
    sequence: int
    event_id: str
    iteration_id: str
    timestamp_utc: str
    event_type: str
    objective_id: str | None
    module_name: str | None
    policy_decision: str | None
    outcome: str
    evidence_directory: str | None
    details: dict[str, Any] = field(default_factory=dict)
    previous_event_hash: str | None = None
    event_hash: str | None = None


@dataclass
class CampaignState:
    campaign_id: str
    campaign_name: str
    campaign_definition_hash: str
    scope_file_hash: str
    rules_of_engagement_reference: str
    authorization_reference: str
    operator_alias: str
    start_time: str
    last_updated_time: str
    current_status: str
    schema_version: str = STATE_SCHEMA_VERSION
    state_revision: int = 0
    next_iteration: int = 1
    elapsed_seconds: float = 0.0
    current_objective_id: str | None = None
    pending_review: dict[str, Any] | None = None
    reviewed_objectives: list[str] = field(default_factory=list)
    completed_modules: list[str] = field(default_factory=list)
    pending_modules: list[str] = field(default_factory=list)
    skipped_modules: list[str] = field(default_factory=list)
    stopped_modules: list[str] = field(default_factory=list)
    finding_candidates: list[str] = field(default_factory=list)
    evidence_directories: list[str] = field(default_factory=list)
    request_counters: dict[str, int] = field(default_factory=lambda: {"total": 0})
    endpoint_request_counters: dict[str, int] = field(default_factory=dict)
    rate_limit_counters: dict[str, int] = field(default_factory=lambda: {"current_minute": 0})
    consecutive_failures: int = 0
    stop_condition_history: list[str] = field(default_factory=list)
    events: list[dict[str, object]] = field(default_factory=list)
    event_log_path: str | None = None
    last_event_hash: str | None = None
    operator_stop_requested: bool = False


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _timestamp_valid(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None


def validate_state(state: CampaignState) -> None:
    if state.schema_version != STATE_SCHEMA_VERSION:
        raise ValueError(f"unsupported campaign state schema: {state.schema_version}")
    if not state.campaign_id or not state.campaign_name:
        raise ValueError("campaign state identity is missing")
    for field_name, value in (
        ("campaign_definition_hash", state.campaign_definition_hash),
        ("scope_file_hash", state.scope_file_hash),
    ):
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"{field_name} must be a lowercase SHA256 digest")
    if state.current_status not in CAMPAIGN_STATUSES:
        raise ValueError(f"unsupported campaign status: {state.current_status}")
    if not _timestamp_valid(state.start_time) or not _timestamp_valid(state.last_updated_time):
        raise ValueError("campaign state timestamps must be timezone-aware ISO-8601 values")
    if state.state_revision < 0 or state.next_iteration < 1 or state.elapsed_seconds < 0:
        raise ValueError("campaign state revision, iteration, and elapsed time cannot be negative")
    if state.consecutive_failures < 0:
        raise ValueError("consecutive failures cannot be negative")
    dispositions = {
        "completed": state.completed_modules,
        "pending": state.pending_modules,
        "skipped": state.skipped_modules,
        "stopped": state.stopped_modules,
    }
    for name, values in dispositions.items():
        if len(values) != len(set(values)):
            raise ValueError(f"{name} objective list contains duplicates")
    names = list(dispositions)
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            overlap = set(dispositions[left]) & set(dispositions[right])
            if overlap:
                raise ValueError(
                    f"objective disposition overlap between {left} and {right}: {', '.join(sorted(overlap))}"
                )
    for counter_name, counter in (
        ("request_counters", state.request_counters),
        ("endpoint_request_counters", state.endpoint_request_counters),
        ("rate_limit_counters", state.rate_limit_counters),
    ):
        if not isinstance(counter, dict) or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in counter.values()
        ):
            raise ValueError(f"{counter_name} values must be non-negative integers")
    if state.current_status == "completed" and (
        state.pending_modules
        or state.stopped_modules
        or state.current_objective_id
        or state.pending_review
    ):
        raise ValueError("completed campaign state cannot retain pending, stopped, or current objectives")
    if state.last_event_hash is not None and (
        len(state.last_event_hash) != 64
        or any(character not in "0123456789abcdef" for character in state.last_event_hash)
    ):
        raise ValueError("last_event_hash must be a lowercase SHA256 digest")
    if state.current_status == "paused_for_human_review":
        if not state.current_objective_id or not state.pending_review:
            raise ValueError("paused campaign state requires a current objective and pending review")
    elif state.pending_review is not None:
        raise ValueError("pending review is only valid while paused for human review")
    if len(state.reviewed_objectives) != len(set(state.reviewed_objectives)):
        raise ValueError("reviewed objective list contains duplicates")


def save_state(state: CampaignState, path: str | Path) -> Path:
    validate_state(state)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    state.state_revision += 1
    payload = asdict(state)
    envelope = {
        "schema_version": STATE_SCHEMA_VERSION,
        "state": payload,
        "sha256": _digest(payload),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(envelope, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_state(path: str | Path) -> CampaignState:
    state_path = Path(path)
    try:
        envelope = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"campaign state could not be read: {state_path}") from exc
    if not isinstance(envelope, dict) or envelope.get("schema_version") != STATE_SCHEMA_VERSION:
        raise ValueError("campaign state envelope is missing or unsupported")
    payload = envelope.get("state")
    if not isinstance(payload, dict) or envelope.get("sha256") != _digest(payload):
        raise ValueError("campaign state integrity check failed")
    try:
        state = CampaignState(**payload)
    except TypeError as exc:
        raise ValueError("campaign state fields are invalid") from exc
    validate_state(state)
    return state
