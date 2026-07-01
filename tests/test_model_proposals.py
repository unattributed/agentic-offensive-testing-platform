from __future__ import annotations

import json

import pytest

from aotp.model_proposals import (
    ModelProposal,
    ModelProposalError,
    parse_model_proposal,
    proposal_json_schema,
)


def _proposal():
    return {
        "objective_id": "http-root-metadata",
        "tool_name": "http_metadata",
        "target_alias": "owned-mail",
        "arguments": {"url": "https://mail.example.invalid/"},
        "rationale": "Collect the approved root metadata.",
    }


def test_model_proposal_round_trips_as_strict_json():
    proposal = parse_model_proposal(json.dumps(_proposal()))
    assert isinstance(proposal, ModelProposal)
    assert proposal.objective_id == "http-root-metadata"
    assert proposal_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize(
    "mutation",
    [
        {"tool_name": "shell"},
        {"objective_id": "../escape"},
        {"target_alias": "Owned Mail"},
        {"rationale": ""},
        {"authorization": True},
    ],
)
def test_model_proposal_rejects_malformed_or_unknown_fields(mutation):
    value = _proposal()
    value.update(mutation)
    with pytest.raises(ModelProposalError, match="malformed"):
        parse_model_proposal(value)


def test_model_proposal_rejects_non_object_json():
    with pytest.raises(ModelProposalError, match="object"):
        parse_model_proposal("[]")
