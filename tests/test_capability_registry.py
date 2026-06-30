from aotp.capability_registry import get_adapter, list_adapters, module_summary


def test_capability_registry_declares_required_web_adapters():
    adapters = {adapter["adapter_id"]: adapter for adapter in list_adapters()}
    assert set(adapters) == {"playwright", "zap", "mitmproxy", "osmap", "browser-suite"}
    for adapter in adapters.values():
        assert adapter["network_silent_default"] is True
        assert adapter["default_execution_mode"] in {"dry_run", "external_reference_only"}
        assert adapter["denied_actions"]
        assert adapter["provenance_requirements"]


def test_playwright_zap_mitmproxy_live_use_is_deferred():
    assert get_adapter("playwright")["live_readiness_status"] == "deferred"
    assert "active_scan_by_default" in get_adapter("zap")["denied_actions"]
    assert "unscoped_interception" in get_adapter("mitmproxy")["denied_actions"]


def test_osmap_and_browser_suite_are_external_reference_only():
    osmap = get_adapter("osmap")
    browser = get_adapter("browser-suite")
    assert "vendored_code" in osmap["denied_actions"]
    assert "dependency_import" in browser["denied_actions"]
    assert browser["default_execution_mode"] == "external_reference_only"
    assert "wstg_web_application" == module_summary()["modules"][0]["module_id"]
