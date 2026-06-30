"""Network-silent deterministic execution boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bounded_fuzzing import build_fuzzing_dry_run_plan
from .control_panel import build_panel_dry_run_observation_plan
from .sbom_review import ingest_sbom_artifact
from .crypto_review import build_crypto_record
from .verifier import Verdict


@dataclass(frozen=True)
class ExecutionResult:
    verdict: str
    tool: str
    request_count: int
    response_metadata: dict[str, Any]


def execute(objective: dict[str, Any], *, live: bool = False) -> ExecutionResult:
    if live:
        return ExecutionResult(
            Verdict.MANUAL_REVIEW,
            "live-adapter-stub",
            0,
            {"status": "live execution is not implemented; no network request was sent"},
        )
    if (
        objective.get("category") == "service_control_panel"
        and (
            objective.get("action") == "plan_safe_panel_observations"
            or objective.get("requested_observations")
        )
    ):
        plan = build_panel_dry_run_observation_plan(objective)
        return ExecutionResult(
            Verdict.INCONCLUSIVE,
            "control-panel-dry-run-planner",
            0,
            {
                "status": "safe panel observations planned only; no network request was sent",
                "observation_plan": plan,
            },
        )
    if objective.get("category") == "bounded_fuzzing":
        plan = build_fuzzing_dry_run_plan(objective)
        return ExecutionResult(
            Verdict.INCONCLUSIVE,
            "bounded-fuzzing-dry-run-planner",
            0,
            {
                "status": "bounded fuzzing planned only; no network request was sent",
                "fuzzing_plan": plan,
            },
        )
    if objective.get("category") == "sbom_review":
        artifact_path = objective.get("_resolved_artifact_path")
        if not isinstance(artifact_path, str):
            raise ValueError("provided SBOM artifact path was not resolved")
        record = ingest_sbom_artifact(
            artifact_path,
            str(objective.get("artifact", "")),
        )
        return ExecutionResult(
            Verdict.INCONCLUSIVE,
            "offline-sbom-review",
            0,
            {
                "status": "provided dependency artifact reviewed locally",
                "sbom_record": record,
            },
        )
    if objective.get("category") == "crypto_controls":
        return ExecutionResult(
            Verdict.INCONCLUSIVE,
            "offline-crypto-controls-review",
            0,
            {
                "status": "provided cryptographic metadata reviewed locally",
                "crypto_record": build_crypto_record(objective),
            },
        )
    return ExecutionResult(
        Verdict.INCONCLUSIVE,
        "deterministic-dry-run",
        0,
        {"status": "planned only; no network request was sent", "action": objective.get("action")},
    )
