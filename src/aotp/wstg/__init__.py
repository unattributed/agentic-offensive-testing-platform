"""WSTG campaign coverage engine."""

from .strategy_map import (
    ExecutableFamily,
    WSTGPhase,
    WSTGStrategyEntry,
    WSTGStrategyMap,
    build_default_strategy_map,
)
from .objective_generator import WSTGCampaignScope, WSTGObjective, generate_wstg_objectives
from .coverage import CoverageDisposition, CoverageRecord, CoverageTracker, choose_next_objective
from .execution_adapter import (
    WSTGAdapterKind,
    WSTGEvidenceRole,
    WSTGExecutionRequest,
    WSTGExecutionResult,
    WSTGExecutionStatus,
    WSTGFindingCandidate,
    WSTGRedactedEvidenceArtifact,
    apply_execution_result_to_coverage,
    build_execution_request,
    coverage_record_from_execution_result,
    create_finding_candidate,
)

__all__ = [
    "CoverageDisposition",
    "CoverageRecord",
    "CoverageTracker",
    "ExecutableFamily",
    "WSTGAdapterKind",
    "WSTGEvidenceRole",
    "WSTGExecutionRequest",
    "WSTGExecutionResult",
    "WSTGExecutionStatus",
    "WSTGFindingCandidate",
    "WSTGRedactedEvidenceArtifact",
    "WSTGCampaignScope",
    "WSTGObjective",
    "WSTGPhase",
    "WSTGStrategyEntry",
    "WSTGStrategyMap",
    "apply_execution_result_to_coverage",
    "build_default_strategy_map",
    "build_execution_request",
    "choose_next_objective",
    "coverage_record_from_execution_result",
    "create_finding_candidate",
    "generate_wstg_objectives",
]
