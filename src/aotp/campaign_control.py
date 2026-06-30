"""Human review and operator stop controls for persisted campaigns."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .campaign_state import CampaignState, save_state
from .config import ConfigError, parse_review_decision
from .evidence import sha256_file, utc_now


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigError("review decided_at_utc is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ConfigError("review decided_at_utc must include a timezone")
    return parsed.astimezone(UTC)


def apply_review_decision(
    state: CampaignState,
    state_path: str | Path,
    review_data: dict[str, Any],
    *,
    now: datetime | None = None,
) -> CampaignState:
    if state.current_status != "paused_for_human_review" or not state.pending_review:
        raise ValueError("campaign is not paused for human review")
    review = parse_review_decision(review_data)
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    decided_at = _parse_time(review.decided_at_utc)
    if decided_at > current_time:
        raise ValueError("review decision is in the future")
    if review.state_sha256 != sha256_file(state_path):
        raise ValueError("review decision state SHA256 does not match checkpoint")
    if review.campaign_id != state.campaign_id:
        raise ValueError("review decision campaign does not match checkpoint")
    if review.objective_id != state.current_objective_id:
        raise ValueError("review decision objective does not match pending review")
    if review.operator_alias != state.operator_alias:
        raise ValueError("review decision operator does not match campaign")

    objective_id = review.objective_id
    phase = state.pending_review.get("phase")
    state.pending_review = None
    state.stop_condition_history.append(
        f"{objective_id}: review {review.decision} ({review.decision_id})"
    )
    if review.decision == "approved":
        if phase == "pre_execution":
            if objective_id not in state.reviewed_objectives:
                state.reviewed_objectives.append(objective_id)
        elif phase == "post_execution":
            state.pending_modules.remove(objective_id)
            state.completed_modules.append(objective_id)
        else:
            raise ValueError("pending review phase is unsupported")
        state.current_objective_id = None
        state.current_status = "ready_to_resume"
    elif review.decision == "denied":
        state.pending_modules.remove(objective_id)
        state.stopped_modules.append(objective_id)
        state.current_objective_id = None
        state.current_status = "stopped_by_condition"
    else:
        state.operator_stop_requested = True
        state.pending_modules.remove(objective_id)
        state.stopped_modules.append(objective_id)
        state.current_objective_id = None
        state.current_status = "stopped_by_operator"
    state.last_updated_time = utc_now()
    save_state(state, state_path)
    return state


def request_operator_stop(state: CampaignState, state_path: str | Path) -> CampaignState:
    if state.current_status in {"completed", "stopped_by_operator"}:
        raise ValueError(f"campaign cannot be stopped from status: {state.current_status}")
    state.operator_stop_requested = True
    state.pending_review = None
    if state.current_objective_id:
        objective_id = state.current_objective_id
        if objective_id in state.pending_modules:
            state.pending_modules.remove(objective_id)
        if objective_id not in state.stopped_modules:
            state.stopped_modules.append(objective_id)
        state.current_objective_id = None
    state.current_status = "stopped_by_operator"
    state.stop_condition_history.append("operator_stop")
    state.last_updated_time = utc_now()
    save_state(state, state_path)
    return state
