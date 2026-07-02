import pytest

from aotp.tool_risk_tiers import ToolRiskTier
from aotp.wstg.catalog import WSTG_V42_CATALOG
from aotp.wstg.strategy_map import (
    ExecutableFamily,
    WSTGPhase,
    WSTGStrategyEntry,
    WSTGStrategyError,
    build_default_strategy_map,
)


def test_default_strategy_map_uses_only_canonical_wstg_v42_titles():
    strategy = build_default_strategy_map()
    entries = strategy.entries()

    assert entries
    assert all(entry.wstg_id.startswith("WSTG-v42-") for entry in entries)
    assert {entry.phase for entry in entries} >= {
        WSTGPhase.PASSIVE,
        WSTGPhase.BROWSER,
        WSTGPhase.AUTH,
        WSTGPhase.INPUT,
        WSTGPhase.VALIDATION,
    }
    assert strategy.by_id("WSTG-v42-INFO-02").family is ExecutableFamily.HTTP_METADATA
    for entry in entries:
        assert entry.name == WSTG_V42_CATALOG.by_id(entry.wstg_id).title


def test_strategy_entry_rejects_non_canonical_wstg_title():
    with pytest.raises(WSTGStrategyError):
        WSTGStrategyEntry(
            wstg_id="WSTG-v42-CLNT-01",
            version="v42",
            category="CLNT",
            name="Browser Route and Client-Side Metadata Review",
            phase=WSTGPhase.BROWSER,
            family=ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA,
            tool_name="playwright_passive_metadata",
            risk_tier=ToolRiskTier.PASSIVE_BROWSER,
            evidence_classification="public",
            evidence_required=("forms",),
        )


def test_strategy_entry_requires_versioned_identifier_and_evidence():
    with pytest.raises(WSTGStrategyError):
        WSTGStrategyEntry(
            wstg_id="WSTG-INFO-02",
            version="v42",
            category="INFO",
            name="bad",
            phase=WSTGPhase.PASSIVE,
            family=ExecutableFamily.HTTP_METADATA,
            tool_name="http_metadata",
            risk_tier=ToolRiskTier.PASSIVE_METADATA,
            evidence_classification="public",
            evidence_required=("headers",),
        )


def test_strategy_map_supports_family_lookup():
    strategy = build_default_strategy_map()

    browser = strategy.by_family(ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA)

    assert len(browser) == 1
    assert browser[0].wstg_id == "WSTG-v42-INFO-06"
    assert browser[0].phase is WSTGPhase.BROWSER


def test_phase_order_is_campaign_order_not_alphabetical():
    from aotp.wstg.strategy_map import phase_order_index

    assert phase_order_index(WSTGPhase.PASSIVE) < phase_order_index(WSTGPhase.BROWSER)
    assert phase_order_index(WSTGPhase.BROWSER) < phase_order_index(WSTGPhase.AUTH)
