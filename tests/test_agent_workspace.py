from __future__ import annotations

import json
import os

import pytest

from aotp.agent_workspace import AgentCampaignWorkspace, AgentWorkspaceError


def test_agent_workspace_is_bounded_private_and_atomic(tmp_path):
    workspace = AgentCampaignWorkspace.create(
        tmp_path / ".aotp" / "campaigns",
        program_alias="owned-program",
        run_id="run-001",
    )
    artifact = workspace.write_json("evidence", "iteration-01", {"safe": True})
    report = workspace.write_text("reports", "due-diligence", "# Safe\n")

    assert artifact.parent == workspace.evidence
    assert report.parent == workspace.reports
    assert json.loads(artifact.read_text()) == {"safe": True}
    assert os.stat(workspace.path).st_mode & 0o777 == 0o700
    assert os.stat(artifact).st_mode & 0o777 == 0o600
    assert os.stat(report).st_mode & 0o777 == 0o600
    assert not list(workspace.path.rglob("*.tmp"))


@pytest.mark.parametrize("value", ["../escape", "/absolute", "MixedCase", "", "a/b"])
def test_agent_workspace_rejects_unsafe_components(tmp_path, value):
    with pytest.raises(AgentWorkspaceError, match="safe lowercase"):
        AgentCampaignWorkspace.create(
            tmp_path / "campaigns",
            program_alias=value,
            run_id="run-001",
        )


def test_agent_workspace_rejects_symlinked_campaign_path(tmp_path):
    root = tmp_path / "campaigns"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "owned-program").symlink_to(outside, target_is_directory=True)
    with pytest.raises(AgentWorkspaceError, match="symlink"):
        AgentCampaignWorkspace.create(
            root,
            program_alias="owned-program",
            run_id="run-001",
        )


def test_agent_workspace_rejects_unapproved_area(tmp_path):
    workspace = AgentCampaignWorkspace.create(
        tmp_path / "campaigns",
        program_alias="owned-program",
        run_id="run-001",
    )
    with pytest.raises(AgentWorkspaceError, match="area"):
        workspace.write_json("vault", "artifact", {})
