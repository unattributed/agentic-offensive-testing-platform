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

__all__ = [
    "CoverageDisposition",
    "CoverageRecord",
    "CoverageTracker",
    "ExecutableFamily",
    "WSTGCampaignScope",
    "WSTGObjective",
    "WSTGPhase",
    "WSTGStrategyEntry",
    "WSTGStrategyMap",
    "build_default_strategy_map",
    "choose_next_objective",
    "generate_wstg_objectives",
]
