"""Browser route and form metadata mapping for WSTG coverage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit


class BrowserMetadataError(ValueError):
    """Raised when browser metadata leaves the approved origin."""


@dataclass(frozen=True)
class BrowserRouteMetadata:
    path: str
    method: str
    wstg_categories: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "method": self.method, "wstg_categories": list(self.wstg_categories)}


@dataclass(frozen=True)
class BrowserFormMetadata:
    action: str
    method: str
    input_names: tuple[str, ...]
    wstg_categories: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "method": self.method,
            "input_names": list(self.input_names),
            "wstg_categories": list(self.wstg_categories),
        }


def map_browser_routes(base_url: str, links: tuple[str, ...]) -> tuple[BrowserRouteMetadata, ...]:
    base = urlsplit(base_url)
    if not base.scheme or not base.hostname:
        raise BrowserMetadataError("base_url must be an absolute URL")
    routes: list[BrowserRouteMetadata] = []
    for link in links:
        resolved = urlsplit(urljoin(base_url, link))
        if resolved.hostname != base.hostname or resolved.scheme != base.scheme:
            raise BrowserMetadataError("browser route metadata left the approved origin")
        path = resolved.path or "/"
        categories = ("INFO", "CLNT") if path == "/" else ("INFO", "ATHN" if "login" in path.lower() else "CLNT")
        routes.append(BrowserRouteMetadata(path=path, method="GET", wstg_categories=categories))
    return tuple(routes)


def map_browser_forms(base_url: str, forms: tuple[dict[str, Any], ...]) -> tuple[BrowserFormMetadata, ...]:
    base = urlsplit(base_url)
    mapped: list[BrowserFormMetadata] = []
    for form in forms:
        action = str(form.get("action") or "/")
        resolved = urlsplit(urljoin(base_url, action))
        if resolved.hostname != base.hostname or resolved.scheme != base.scheme:
            raise BrowserMetadataError("browser form action left the approved origin")
        method = str(form.get("method") or "GET").upper()
        inputs = tuple(sorted(str(item) for item in form.get("input_names", ()) if item))
        categories = ("INPV", "ATHN") if any("pass" in item.lower() for item in inputs) else ("INPV",)
        mapped.append(
            BrowserFormMetadata(
                action=resolved.path or "/",
                method=method,
                input_names=inputs,
                wstg_categories=categories,
            )
        )
    return tuple(mapped)
