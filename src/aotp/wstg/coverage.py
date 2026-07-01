"""Coverage tracking and next-objective choice for WSTG campaigns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .objective_generator import WSTGObjective
from .strategy_map import WSTGPhase, phase_order_index


class CoverageDisposition(str, Enum):
    TESTED = "tested"
    SKIPPED = "skipped"
    DENIED = "denied"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class CoverageRecord:
    objective_id: str
    wstg_id: str
    phase: WSTGPhase
    disposition: CoverageDisposition
    evidence_references: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.disposition is CoverageDisposition.TESTED and not self.evidence_references:
            raise ValueError("tested coverage records require evidence references")
        if self.disposition is not CoverageDisposition.TESTED and not self.reasons:
            raise ValueError("non-tested coverage records require reasons")

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "wstg_id": self.wstg_id,
            "phase": self.phase.value,
            "disposition": self.disposition.value,
            "evidence_references": list(self.evidence_references),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class NextObjectiveDecision:
    objective: WSTGObjective | None
    action: str
    reason: str
    evidence_inputs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective.objective_id if self.objective else None,
            "wstg_id": self.objective.wstg_id if self.objective else None,
            "action": self.action,
            "reason": self.reason,
            "evidence_inputs": list(self.evidence_inputs),
        }


class CoverageTracker:
    """Mutable coverage ledger with explicit dispositions."""

    def __init__(self, objectives: Iterable[WSTGObjective]) -> None:
        self._objectives = tuple(objectives)
        ids = [objective.objective_id for objective in self._objectives]
        if len(ids) != len(set(ids)):
            raise ValueError("WSTG objective identifiers must be unique")
        self._records: dict[str, CoverageRecord] = {}

    @property
    def objectives(self) -> tuple[WSTGObjective, ...]:
        return self._objectives

    def record(self, record: CoverageRecord) -> None:
        objective_ids = {objective.objective_id for objective in self._objectives}
        if record.objective_id not in objective_ids:
            raise ValueError("coverage record references an unknown objective")
        self._records[record.objective_id] = record

    def mark(
        self,
        objective: WSTGObjective,
        disposition: CoverageDisposition,
        *,
        evidence_references: tuple[str, ...] = (),
        reasons: tuple[str, ...] = (),
    ) -> CoverageRecord:
        record = CoverageRecord(
            objective_id=objective.objective_id,
            wstg_id=objective.wstg_id,
            phase=objective.phase,
            disposition=disposition,
            evidence_references=evidence_references,
            reasons=reasons,
        )
        self.record(record)
        return record

    def records(self) -> tuple[CoverageRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def missing(self) -> tuple[WSTGObjective, ...]:
        tested_or_final = {
            key
            for key, record in self._records.items()
            if record.disposition in {
                CoverageDisposition.TESTED,
                CoverageDisposition.SKIPPED,
                CoverageDisposition.DENIED,
                CoverageDisposition.BLOCKED,
            }
        }
        return tuple(objective for objective in self._objectives if objective.objective_id not in tested_or_final)

    def gap_summary(self) -> dict[str, Any]:
        statuses = {disposition.value: 0 for disposition in CoverageDisposition}
        for record in self._records.values():
            statuses[record.disposition.value] += 1
        deferred_count = len(self.missing())
        statuses[CoverageDisposition.DEFERRED.value] += deferred_count
        phase_status: dict[str, dict[str, int]] = {phase.value: {key: 0 for key in statuses} for phase in WSTGPhase}
        for objective in self._objectives:
            record = self._records.get(objective.objective_id)
            disposition = record.disposition if record else CoverageDisposition.DEFERRED
            phase_status[objective.phase.value][disposition.value] += 1
        return {
            "total_objectives": len(self._objectives),
            "statuses": statuses,
            "phases": phase_status,
            "gaps": [objective.objective_id for objective in self.missing()],
        }


def choose_next_objective(
    objectives: Iterable[WSTGObjective],
    tracker: CoverageTracker,
    *,
    evidence_summaries: Iterable[dict[str, Any]] = (),
) -> NextObjectiveDecision:
    """Choose the next objective from explicit coverage gaps with explainable reasoning."""

    objective_set = tuple(objectives)
    missing = tracker.missing()
    evidence_refs = tuple(
        str(item.get("artifact_reference") or item.get("evidence_path") or item.get("objective_id"))
        for item in evidence_summaries
        if item.get("artifact_reference") or item.get("evidence_path") or item.get("objective_id")
    )
    if not missing:
        return NextObjectiveDecision(
            objective=None,
            action="stop",
            reason="all approved WSTG objectives have explicit coverage dispositions",
            evidence_inputs=evidence_refs,
        )
    objective = sorted(missing, key=lambda item: (phase_order_index(item.phase), item.wstg_id))[0]
    return NextObjectiveDecision(
        objective=objective,
        action="continue",
        reason=(
            f"selected {objective.wstg_id} because it is the earliest approved uncovered "
            f"{objective.phase.value} phase objective"
        ),
        evidence_inputs=evidence_refs,
    )


def render_coverage_report(
    tracker: CoverageTracker,
    *,
    campaign_id: str,
    target_alias: str,
    decision: NextObjectiveDecision | None = None,
) -> str:
    summary = tracker.gap_summary()
    lines = [
        "# WSTG Campaign Coverage Report",
        "",
        f"- Campaign: `{campaign_id}`",
        f"- Target alias: `{target_alias}`",
        f"- Total objectives: {summary['total_objectives']}",
        "",
        "## Disposition summary",
        "",
    ]
    for status, count in summary["statuses"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Objective records", ""])
    for objective in tracker.objectives:
        record = next((item for item in tracker.records() if item.objective_id == objective.objective_id), None)
        disposition = record.disposition.value if record else CoverageDisposition.DEFERRED.value
        evidence = ", ".join(record.evidence_references) if record and record.evidence_references else "none"
        lines.append(f"- `{objective.wstg_id}` `{objective.phase.value}` `{disposition}` evidence: {evidence}")
    if decision is not None:
        lines.extend(["", "## Continue or stop", "", f"- Action: `{decision.action}`", f"- Reason: {decision.reason}"])
    lines.append("")
    return "\n".join(lines)
