from aotp.wstg_case_registry import build_dry_run_record, case_ids, get_case, list_cases


def test_wstg_case_registry_is_deterministic_and_version_aware():
    first = [case["case_id"] for case in list_cases()]
    second = [case["case_id"] for case in list_cases()]
    assert first == sorted(first)
    assert first == second
    smoke = get_case("wstg-registry-smoke")
    assert smoke["module"] == "wstg_web_application"
    assert smoke["wstg"][0]["version"] == "4.2"
    assert smoke["approved_actions"]
    assert "network_request" in smoke["denied_actions"]
    assert "network_silent" in smoke["adapter_capability_requirements"]


def test_wstg_case_dry_run_record_is_network_silent():
    record = build_dry_run_record("wstg-registry-smoke")
    assert record["execution_mode"] == "dry_run"
    assert record["request_count"] == 0
    assert record["policy_decision"] == "allowed_dry_run"
