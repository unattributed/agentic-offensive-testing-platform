import subprocess

import pytest

from aotp.agent_tools.zap_passive import (
    ZapPassiveError,
    build_zap_passive_command,
    run_zap_passive_baseline,
    validate_zap_output_scope,
)


def test_zap_passive_command_uses_baseline_passive_options(tmp_path):
    argv = build_zap_passive_command(
        "https://example.com/",
        max_minutes=1,
        zap_binary="zap-baseline.py",
        output_dir=tmp_path,
    )
    assert argv[:6] == ("zap-baseline.py", "-t", "https://example.com/", "-m", "1", "-I")
    assert "-a" not in argv
    assert "-z" not in argv
    assert "--hook" not in argv
    assert "-U" not in argv
    assert "-J" in argv
    assert "-r" in argv


@pytest.mark.parametrize(
    "url",
    ["https://user@example.com/", "https://example.com/?q=1", "ftp://example.com/", ""],
)
def test_zap_passive_denies_unsafe_targets(url):
    with pytest.raises(ZapPassiveError):
        build_zap_passive_command(url)


def test_zap_passive_runner_is_bounded():
    observed = {}

    def fake_runner(argv, *, timeout):
        observed["argv"] = argv
        observed["timeout"] = timeout
        return subprocess.CompletedProcess(argv, 0, stdout="PASS: Example\n", stderr="")

    result = run_zap_passive_baseline(
        "https://example.com/",
        max_minutes=1,
        runner=fake_runner,
        zap_binary="zap-baseline.py",
    )
    assert observed["timeout"] == 300
    assert "-m" in observed["argv"]
    assert result.tool_name == "zap_passive_baseline"
    assert result.request_count == 1
    assert result.result["returncode"] == 0


def test_zap_passive_output_scope_allows_same_origin_urls():
    validate_zap_output_scope(
        "https://example.com/",
        "PASS https://example.com/robots.txt and https://example.com/.well-known/security.txt",
    )


def test_zap_passive_output_scope_denies_out_of_scope_urls():
    with pytest.raises(ZapPassiveError):
        validate_zap_output_scope("https://example.com/", "WARN https://other.example/admin")


def test_zap_passive_runner_denies_out_of_scope_output():
    def fake_runner(argv, *, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="WARN https://other.example/admin", stderr="")

    with pytest.raises(ZapPassiveError):
        run_zap_passive_baseline(
            "https://example.com/",
            max_minutes=1,
            runner=fake_runner,
            zap_binary="zap-baseline.py",
        )
