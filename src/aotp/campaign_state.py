"""Persistent campaign state and event records."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class CampaignEvent:
    iteration_id: str
    timestamp_utc: str
    objective_id: str
    module_name: str
    policy_decision: str
    outcome: str
    evidence_directory: str | None


@dataclass
class CampaignState:
    campaign_id: str
    campaign_name: str
    scope_file_hash: str
    rules_of_engagement_reference: str
    authorization_reference: str
    start_time: str
    last_updated_time: str
    current_status: str
    completed_modules: list[str] = field(default_factory=list)
    pending_modules: list[str] = field(default_factory=list)
    skipped_modules: list[str] = field(default_factory=list)
    stopped_modules: list[str] = field(default_factory=list)
    finding_candidates: list[str] = field(default_factory=list)
    evidence_directories: list[str] = field(default_factory=list)
    request_counters: dict[str, int] = field(default_factory=lambda: {"total": 0})
    rate_limit_counters: dict[str, int] = field(default_factory=lambda: {"current_minute": 0})
    stop_condition_history: list[str] = field(default_factory=list)
    events: list[dict[str, object]] = field(default_factory=list)
    operator_stop_requested: bool = False


def save_state(state: CampaignState, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def load_state(path: str | Path) -> CampaignState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return CampaignState(**data)
