import pytest

from aotp.agent_tools.playwright_passive import (
    PlaywrightPassiveError,
    collect_playwright_passive_metadata,
    validate_browser_metadata_url,
    validate_same_origin_navigation,
)


def test_playwright_passive_accepts_credential_free_http_url():
    assert validate_browser_metadata_url("https://example.com/") == "https://example.com/"


@pytest.mark.parametrize(
    "url",
    ["https://user@example.com/", "https://example.com/#frag", "https://example.com/?q=1", "file:///tmp/x"],
)
def test_playwright_passive_denies_unsafe_url(url):
    with pytest.raises(PlaywrightPassiveError):
        validate_browser_metadata_url(url)


def test_playwright_passive_uses_injected_collector_without_browser_dependency():
    def fake_collector(url):
        return {
            "url": url,
            "final_url": url,
            "status": 200,
            "title": "Example",
            "frame_count": 1,
            "link_count": 0,
            "form_count": 0,
        }

    result = collect_playwright_passive_metadata("https://example.com/", collector=fake_collector)
    assert result.tool_name == "playwright_passive_metadata"
    assert result.request_count == 1
    assert result.result["form_count"] == 0


def test_playwright_passive_denies_cross_origin_final_url():
    with pytest.raises(PlaywrightPassiveError):
        validate_same_origin_navigation("https://example.com/", "https://evil.example/")


def test_playwright_passive_denies_collector_redirect_out_of_scope():
    def fake_collector(_url):
        return {
            "url": "https://example.com/",
            "final_url": "https://other.example/",
            "status": 200,
            "title": "Other",
            "frame_count": 1,
            "link_count": 0,
            "form_count": 0,
        }

    with pytest.raises(PlaywrightPassiveError):
        collect_playwright_passive_metadata("https://example.com/", collector=fake_collector)
