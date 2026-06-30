from copy import deepcopy

import pytest

from aotp.campaign import load_campaign, objective_ids, parse_campaign
from aotp.config import ConfigError, load_yaml


@pytest.mark.parametrize(
    "name",
    [
        "authorized-webapp-campaign.example.yaml",
        "sbom-config-crypto-campaign.example.yaml",
        "bug-bounty-efficiency-campaign.example.yaml",
    ],
)
def test_example_campaigns_parse_as_strict_execution_contracts(project_root, name):
    campaign = load_campaign(str(project_root / "campaigns" / name)).data
    parsed = parse_campaign(campaign)
    assert parsed.limits.max_iterations > 0
    assert parsed.stop_conditions[:3] == ("operator_stop", "policy_denial", "human_review")
    assert objective_ids(campaign)


def test_campaign_rejects_duplicate_objective_ids(project_root):
    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    campaign["objectives"][1]["id"] = campaign["objectives"][0]["id"]
    with pytest.raises(ConfigError, match="ids must not contain duplicates"):
        parse_campaign(campaign)


def test_campaign_rejects_unknown_dependency(project_root):
    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    campaign["objectives"][1]["depends_on"] = ["missing-objective"]
    with pytest.raises(ConfigError, match="unknown dependencies"):
        parse_campaign(campaign)


def test_campaign_rejects_dependency_cycle(project_root):
    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    campaign["objectives"][0]["depends_on"] = ["wstg-authn-session"]
    with pytest.raises(ConfigError, match="dependency cycle"):
        parse_campaign(campaign)


def test_campaign_rejects_unknown_fields_and_live_default(project_root):
    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    campaign["discover_targets"] = True
    with pytest.raises(ConfigError, match="unknown fields"):
        parse_campaign(campaign)

    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    campaign["execution"]["default_mode"] = "live"
    with pytest.raises(ConfigError, match="must be dry_run"):
        parse_campaign(campaign)


def test_campaign_parse_does_not_mutate_source(project_root):
    campaign = load_yaml(project_root / "campaigns/authorized-webapp-campaign.example.yaml").data
    original = deepcopy(campaign)
    parse_campaign(campaign)
    assert campaign == original
