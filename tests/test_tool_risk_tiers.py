import pytest

from aotp.tool_risk_tiers import (
    RISK_TIER_DEFINITIONS,
    ToolRiskTier,
    parse_risk_tier,
    risk_tier_definition,
    risk_tier_rank,
    risk_tier_within_maximum,
)


def test_all_risk_tiers_have_documented_definitions():
    assert set(RISK_TIER_DEFINITIONS) == set(ToolRiskTier)
    for tier in ToolRiskTier:
        definition = risk_tier_definition(tier)
        assert definition.tier == tier
        assert definition.summary
        assert definition.default_evidence_classification in {"public", "restricted", "secret"}


def test_risk_tiers_are_ordered_from_passive_to_exploitation():
    assert risk_tier_rank(ToolRiskTier.PASSIVE_METADATA) < risk_tier_rank(ToolRiskTier.SERVICE_FINGERPRINT)
    assert risk_tier_rank(ToolRiskTier.SERVICE_FINGERPRINT) < risk_tier_rank(ToolRiskTier.EXPLOITATION_VALIDATION)
    assert risk_tier_within_maximum(ToolRiskTier.PASSIVE_METADATA, ToolRiskTier.PASSIVE_SCANNER)
    assert not risk_tier_within_maximum(ToolRiskTier.EXPLOITATION_VALIDATION, ToolRiskTier.PASSIVE_SCANNER)


def test_unknown_risk_tier_fails_closed():
    with pytest.raises(ValueError):
        parse_risk_tier("magic")
