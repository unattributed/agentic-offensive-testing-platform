import subprocess

import pytest

from aotp.agent_tools.nmap_governed import (
    NmapGovernedError,
    build_nmap_command,
    run_governed_nmap,
    validate_single_host,
)


def test_nmap_command_is_single_host_single_port():
    argv = build_nmap_command("example.com", 443, nmap_binary="nmap")
    assert argv == (
        "nmap",
        "-Pn",
        "-sV",
        "--version-light",
        "--max-retries",
        "1",
        "--host-timeout",
        "30s",
        "-p",
        "443",
        "--",
        "example.com",
    )


@pytest.mark.parametrize("host", ["example.com/24", "*.example.com", "example.com other", ""])
def test_nmap_denies_target_expansion(host):
    with pytest.raises(NmapGovernedError):
        validate_single_host(host)


def test_governed_nmap_uses_fixed_arguments():
    observed = {}

    def fake_runner(argv, *, timeout):
        observed["argv"] = argv
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(argv, 0, stdout="443/tcp open https\n", stderr="")

    result = run_governed_nmap(
        "example.com",
        443,
        "https",
        runner=fake_runner,
        nmap_binary="/usr/bin/nmap",
    )
    assert observed["argv"][0] == "/usr/bin/nmap"
    assert "--script" not in observed["argv"]
    assert observed["argv"][-1] == "example.com"
    assert result.tool_name == "nmap_governed"
    assert result.request_count == 1
    assert result.result["port"] == 443
