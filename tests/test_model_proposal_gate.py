from __future__ import annotations

from dataclasses import replace

import pytest

from aotp.model_proposal_gate import (
    ProposalPolicyError,
    build_sprint14_policy,
    evaluate_model_proposal,
)
from aotp.model_proposals import ModelProposal


def _policy():
    return build_sprint14_policy(
        campaign_id="sprint14-run",
        program_alias="owned-program",
        target_alias="owned-mail",
        base_url="https://mail.example.invalid/",
        authorization_reference="owner-approved-sprint14",
        operator_approved=True,
    )


def _proposal(objective_index=0):
    objective = _policy().objectives[objective_index]
    return ModelProposal(
        objective_id=objective.objective_id,
        tool_name=objective.tool_name,
        target_alias="owned-mail",
        arguments=objective.arguments,
        rationale="Advance approved metadata coverage.",
    )


def test_approved_exact_proposal_passes():
    decision = evaluate_model_proposal(_proposal(), _policy(), completed=set())
    assert decision.allowed is True
    assert decision.summary == "allowed"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("target_alias", "other-target", "outside"),
        ("tool_name", "tls_metadata", "tool"),
        ("arguments", {"url": "https://other.example.invalid/"}, "arguments"),
        ("objective_id", "unknown", "remaining"),
    ],
)
def test_out_of_scope_or_mutated_proposals_are_denied(field, value, message):
    proposal = _proposal().model_copy(update={field: value})
    decision = evaluate_model_proposal(proposal, _policy(), completed=set())
    assert decision.allowed is False
    assert message in decision.summary


def test_completed_objective_cannot_be_replayed():
    proposal = _proposal()
    decision = evaluate_model_proposal(
        proposal,
        _policy(),
        completed={proposal.objective_id},
    )
    assert decision.allowed is False
    assert "remaining" in decision.summary


@pytest.mark.parametrize(
    "changes",
    [
        {"base_url": "http://mail.example.invalid/"},
        {"operator_approved": False},
        {"authorization_reference": "placeholder"},
        {"max_iterations": 4},
        {"max_requests": 3},
        {"objectives": ()},
        {"target_alias": "../escape"},
    ],
)
def test_campaign_policy_fails_closed(changes):
    with pytest.raises(ProposalPolicyError):
        replace(_policy(), **changes)
