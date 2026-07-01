import subprocess

import pytest

from aotp.agent_tools.campaign_shell import (
    CampaignShellError,
    list_allowed_shell_commands,
    run_campaign_shell_command,
)


def test_campaign_shell_exposes_only_allowlisted_command_ids():
    command_ids = {item.command_id for item in list_allowed_shell_commands()}
    assert "python-version" in command_ids
    assert "rm -rf /" not in command_ids


def test_campaign_shell_denies_arbitrary_commands():
    with pytest.raises(CampaignShellError):
        run_campaign_shell_command("python-version; id")


def test_campaign_shell_executes_fixed_argv_only():
    observed = {}

    def fake_runner(argv, *, timeout):
        observed["argv"] = argv
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(argv, 0, stdout="Python 3.11.0\n", stderr="")

    result = run_campaign_shell_command("python-version", runner=fake_runner)
    assert observed["argv"][-1] == "--version"
    assert ";" not in " ".join(observed["argv"])
    assert observed["timeout"] == 15
    assert result.tool_name == "campaign_shell"
    assert result.request_count == 0
    assert result.result["returncode"] == 0
