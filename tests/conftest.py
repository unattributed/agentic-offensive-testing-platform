from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aotp.config import load_yaml


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def example_scope(project_root: Path) -> dict:
    return deepcopy(load_yaml(project_root / "config/scope.example.yaml").data)


@pytest.fixture
def authorized_scope(example_scope: dict) -> dict:
    scope = deepcopy(example_scope)
    scope["authorization"].update(
        {
            "live_authorized": True,
            "type": "bug_bounty_program",
            "reference": "authorization-record-2026",
            "agreement_reference": "accepted-program-policy-2026",
            "program_profile_reference": "private-program-profile",
            "issued_at_utc": "2026-01-01T00:00:00Z",
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
        }
    )
    scope["rules_of_engagement"].update(
        {
            "confirmed": True,
            "reference": "roe-record-2026",
            "confirmed_at_utc": "2026-01-02T00:00:00Z",
            "policy_sha256": "a" * 64,
            "prohibited_actions_acknowledged": True,
            "evidence_handling_confirmed": True,
            "emergency_contact_reference": "private-emergency-contact-record",
            "target_instability_stop": True,
            "authentication_lockout_stop": True,
        }
    )
    scope["allowed_test_windows"] = [
        {
            "label": "authorized-2026-window",
            "start_utc": "2026-01-01T00:00:00Z",
            "end_utc": "2027-01-01T00:00:00Z",
        }
    ]
    return scope


@pytest.fixture
def authorized_profile(project_root: Path) -> dict:
    profile = deepcopy(load_yaml(project_root / "config/program-profile.example.yaml").data)
    profile.update(
        {
            "platform_reference": "program-platform-record",
            "accepted_policy_date": "2026-01-01",
            "authorization_reference": "authorization-record-2026",
            "safe_harbor_reference": "safe-harbor-record-2026",
            "policy_sha256": "a" * 64,
        }
    )
    return profile


@pytest.fixture
def authorized_now() -> datetime:
    return datetime(2026, 6, 30, 0, 0, tzinfo=UTC)


@pytest.fixture
def authorized_objective() -> dict:
    return {
        "id": "authorized-security-headers",
        "target_alias": "local-placeholder",
        "category": "wstg_webapp",
        "action": "observe_security_headers",
        "service": "https",
        "environment": "isolated-example-environment",
        "account_alias": "provisioned-example-account",
    }


@pytest.fixture
def authorized_scope_sha256() -> str:
    return "b" * 64


@pytest.fixture
def authorized_approval(authorized_scope_sha256: str) -> dict:
    return {
        "schema_version": "1.0",
        "approval_id": "operator-approval-2026",
        "operator_alias": "example-operator",
        "decision": "approved",
        "approved_at_utc": "2026-06-29T00:00:00Z",
        "valid_until_utc": "2026-07-01T00:00:00Z",
        "scope_sha256": authorized_scope_sha256,
        "authorization_reference": "authorization-record-2026",
        "objective_ids": ["authorized-security-headers"],
        "campaign_ids": [],
    }
