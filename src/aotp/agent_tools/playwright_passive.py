"""Passive Playwright browser metadata wrapper."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from .http_metadata import ToolExecutionResult


class PlaywrightPassiveError(RuntimeError):
    """Raised when passive browser metadata collection is unsafe or unavailable."""


def validate_browser_metadata_url(url: str) -> str:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise PlaywrightPassiveError(
            "Playwright passive URL must be credential-free HTTP or HTTPS without query or fragment"
        )
    return url


def _origin_tuple(url: str) -> tuple[str, str, int]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
        raise PlaywrightPassiveError("Playwright passive URL has no comparable origin")
    default_port = 443 if parsed.scheme == "https" else 80
    return parsed.scheme, parsed.hostname.lower().rstrip("."), parsed.port or default_port


def validate_same_origin_navigation(start_url: str, final_url: str) -> str:
    """Reject browser navigation that leaves the approved origin."""

    validate_browser_metadata_url(start_url)
    validate_browser_metadata_url(final_url)
    if _origin_tuple(start_url) != _origin_tuple(final_url):
        raise PlaywrightPassiveError("Playwright passive navigation left the approved origin")
    return final_url


def _collect_with_playwright(url: str, *, timeout_ms: int) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise PlaywrightPassiveError("playwright is not available") from exc
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(ignore_https_errors=False)
            page = context.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            title = page.title()
            frame_count = len(page.frames)
            link_count = page.locator("a[href]").count()
            form_count = page.locator("form").count()
            final_url = validate_same_origin_navigation(url, page.url)
            return {
                "url": url,
                "final_url": final_url,
                "status": response.status if response is not None else None,
                "title": title[:200],
                "frame_count": frame_count,
                "link_count": link_count,
                "form_count": form_count,
            }
        finally:
            browser.close()


def collect_playwright_passive_metadata(
    url: str,
    *,
    timeout_ms: int = 15000,
    collector: Callable[[str], dict[str, Any]] | None = None,
) -> ToolExecutionResult:
    """Collect single-page passive browser metadata, never submit forms or click controls."""

    safe_url = validate_browser_metadata_url(url)
    if timeout_ms < 1000 or timeout_ms > 60000:
        raise PlaywrightPassiveError("Playwright passive timeout must be from 1000 to 60000 ms")
    try:
        result = collector(safe_url) if collector is not None else _collect_with_playwright(safe_url, timeout_ms=timeout_ms)
        if not isinstance(result, dict) or not isinstance(result.get("final_url"), str):
            raise PlaywrightPassiveError("Playwright passive collector must return a final_url")
        validate_same_origin_navigation(safe_url, result["final_url"])
    except PlaywrightPassiveError:
        raise
    except Exception as exc:
        raise PlaywrightPassiveError("Playwright passive collection failed") from exc
    return ToolExecutionResult(
        tool_name="playwright_passive_metadata",
        request_count=1,
        result=result,
    )
