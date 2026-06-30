"""Append-only hash-chained campaign event logging."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .campaign_state import CampaignEvent, CampaignState
from .evidence import utc_now


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _event_hash(event: CampaignEvent) -> str:
    payload = asdict(event)
    payload.pop("event_hash", None)
    return hashlib.sha256(_canonical(payload)).hexdigest()


def resolve_event_log(state: CampaignState, state_path: str | Path) -> Path:
    if not state.event_log_path:
        raise ValueError("campaign state has no event log path")
    path = Path(state.event_log_path)
    if path.is_absolute():
        raise ValueError("campaign event log path must be relative")
    state_file = Path(state_path).resolve()
    if state_file.parent.name == "state" and state_file.parent.parent.name == ".aotp":
        root = state_file.parent.parent.parent
    else:
        root = state_file.parent
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("campaign event log path escapes workspace") from exc
    return resolved


def append_campaign_event(
    state: CampaignState,
    state_path: str | Path,
    *,
    event_type: str,
    outcome: str,
    objective_id: str | None = None,
    module_name: str | None = None,
    policy_decision: str | None = None,
    evidence_directory: str | None = None,
    iteration_id: str = "0000",
    details: dict[str, Any] | None = None,
) -> CampaignEvent:
    event = CampaignEvent(
        sequence=len(state.events) + 1,
        event_id=str(uuid.uuid4()),
        iteration_id=iteration_id,
        timestamp_utc=utc_now(),
        event_type=event_type,
        objective_id=objective_id,
        module_name=module_name,
        policy_decision=policy_decision,
        outcome=outcome,
        evidence_directory=evidence_directory,
        details=details or {},
        previous_event_hash=state.last_event_hash,
    )
    event.event_hash = _event_hash(event)
    path = resolve_event_log(state, state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.chmod(path, 0o600)
    state.events.append(asdict(event))
    state.last_event_hash = event.event_hash
    return event


def verify_event_log(path: str | Path) -> list[str]:
    event_path = Path(path)
    if not event_path.is_file():
        return ["campaign event log does not exist"]
    failures: list[str] = []
    previous_hash: str | None = None
    expected_sequence = 1
    try:
        lines = event_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"campaign event log could not be read: {exc}"]
    if not lines:
        return ["campaign event log is empty"]
    for line_number, line in enumerate(lines, 1):
        try:
            data = json.loads(line)
            event = CampaignEvent(**data)
        except (json.JSONDecodeError, TypeError) as exc:
            failures.append(f"line {line_number} is invalid: {exc}")
            continue
        if event.sequence != expected_sequence:
            failures.append(f"line {line_number} sequence is not contiguous")
        if event.previous_event_hash != previous_hash:
            failures.append(f"line {line_number} previous hash does not match")
        calculated = _event_hash(event)
        if event.event_hash != calculated:
            failures.append(f"line {line_number} event hash does not match")
        previous_hash = event.event_hash
        expected_sequence += 1
    return failures


def verify_state_event_log(state: CampaignState, state_path: str | Path) -> list[str]:
    path = resolve_event_log(state, state_path)
    failures = verify_event_log(path)
    if not failures:
        lines = path.read_text(encoding="utf-8").splitlines()
        final = json.loads(lines[-1])
        if final.get("event_hash") != state.last_event_hash:
            failures.append("campaign state last event hash does not match event log")
        if len(lines) != len(state.events):
            failures.append("campaign state event count does not match event log")
    return failures
