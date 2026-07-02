"""Local-only OSMAP source metadata review.

This module never imports, executes, clones, or vendors reviewed source. It reads
only local directories or local zip archives and emits hashes plus safe route and
authentication hints for downstream campaign planning.
"""

from __future__ import annotations

import hashlib
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import urlsplit


class OSMAPSourceReviewError(ValueError):
    """Raised when local OSMAP source review is unsafe or unsupported."""


_TEXT_SUFFIXES = {".py", ".rs", ".go", ".js", ".ts", ".html", ".jinja", ".toml", ".yaml", ".yml"}
_ROUTE_PATTERNS = (
    re.compile(r"@(?:app|router|blueprint)\.(get|post|put|patch|delete|route)\(\s*[\"']([^\"']+)[\"']", re.I),
    re.compile(r"\.(get|post|put|patch|delete|route)\(\s*[\"']([^\"']+)[\"']", re.I),
    re.compile(r"#\[(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']\s*\)\]", re.I),
)
_METHODS_PATTERN = re.compile(r"methods\s*=\s*\[([^\]]+)\]", re.I)
_AUTH_TERMS = {
    "login": "login",
    "logout": "logout",
    "require_auth": "require_auth",
    "requires_auth": "require_auth",
    "authenticated": "authenticated",
    "session": "session",
    "csrf": "csrf",
    "cookie": "cookie",
    "bearer": "bearer",
}
_FRAMEWORK_TERMS = {
    "flask": "flask",
    "fastapi": "fastapi",
    "starlette": "starlette",
    "axum": "axum",
    "rocket": "rocket",
    "actix": "actix",
}


@dataclass(frozen=True)
class SourceFileMetadata:
    relative_path: str
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, object]:
        return {"relative_path": self.relative_path, "sha256": self.sha256, "size_bytes": self.size_bytes}


@dataclass(frozen=True)
class SourceRouteCandidate:
    method: str
    path_pattern: str
    source_reference: str
    handler_reference: str
    evidence_sha256: str
    auth_hints: tuple[str, ...]
    confidence: str

    def as_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "path_pattern": self.path_pattern,
            "source_reference": self.source_reference,
            "handler_reference": self.handler_reference,
            "evidence_sha256": self.evidence_sha256,
            "auth_hints": list(self.auth_hints),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class SourceReviewResult:
    source_kind: str
    source_reference: str
    source_root_hash: str
    file_count: int
    selected_files: tuple[SourceFileMetadata, ...]
    route_candidates: tuple[SourceRouteCandidate, ...]
    framework_indicators: tuple[str, ...]
    auth_indicators: tuple[str, ...]
    ignored_file_reasons: dict[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "source_reference": self.source_reference,
            "source_root_hash": self.source_root_hash,
            "file_count": self.file_count,
            "selected_files": [item.as_dict() for item in self.selected_files],
            "route_candidates": [item.as_dict() for item in self.route_candidates],
            "framework_indicators": list(self.framework_indicators),
            "auth_indicators": list(self.auth_indicators),
            "ignored_file_reasons": dict(self.ignored_file_reasons),
            "warnings": list(self.warnings),
            "redacted": True,
        }


def review_osmap_source(source: str | Path, *, workspace: str | Path | None = None) -> SourceReviewResult:
    """Review a local OSMAP repository directory or zip archive for safe metadata."""

    source_path = _validate_local_source(source, workspace=workspace)
    if source_path.is_dir():
        return _review_directory(source_path)
    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        return _review_zip(source_path)
    raise OSMAPSourceReviewError("OSMAP source must be a local directory or zip archive")


def _validate_local_source(source: str | Path, *, workspace: str | Path | None) -> Path:
    text = str(source)
    parsed = urlsplit(text)
    if parsed.scheme and parsed.scheme not in {""}:
        raise OSMAPSourceReviewError("remote source URLs are not allowed")
    path = Path(text).expanduser().resolve()
    if not path.exists():
        raise OSMAPSourceReviewError("source path does not exist")
    if path.is_symlink():
        raise OSMAPSourceReviewError("source path must not be a symlink")
    if workspace is not None:
        root = Path(workspace).expanduser().resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise OSMAPSourceReviewError("source path is outside the review workspace") from exc
    return path


def _review_directory(root: Path) -> SourceReviewResult:
    selected: list[SourceFileMetadata] = []
    routes: list[SourceRouteCandidate] = []
    ignored: dict[str, str] = {}
    framework_indicators: set[str] = set()
    auth_indicators: set[str] = set()
    warnings: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise OSMAPSourceReviewError(f"unsafe symlink in source tree: {rel}")
        if not path.is_file():
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES:
            ignored[rel] = "unsupported suffix"
            continue
        payload = path.read_bytes()
        file_hash = hashlib.sha256(payload).hexdigest()
        selected.append(SourceFileMetadata(relative_path=rel, sha256=file_hash, size_bytes=len(payload)))
        text = payload.decode("utf-8", "replace")
        framework_indicators.update(_find_terms(text, _FRAMEWORK_TERMS))
        auth_indicators.update(_find_terms(text, _AUTH_TERMS))
        routes.extend(_extract_routes(rel, text, file_hash))
    return _build_result(
        source_kind="directory",
        source_reference=root.name,
        selected=selected,
        routes=routes,
        framework_indicators=framework_indicators,
        auth_indicators=auth_indicators,
        ignored=ignored,
        warnings=warnings,
    )


def _review_zip(path: Path) -> SourceReviewResult:
    selected: list[SourceFileMetadata] = []
    routes: list[SourceRouteCandidate] = []
    ignored: dict[str, str] = {}
    framework_indicators: set[str] = set()
    auth_indicators: set[str] = set()
    warnings: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            rel = _validate_zip_member(info)
            if rel is None:
                continue
            if Path(rel).suffix.lower() not in _TEXT_SUFFIXES:
                ignored[rel] = "unsupported suffix"
                continue
            payload = archive.read(info)
            file_hash = hashlib.sha256(payload).hexdigest()
            selected.append(SourceFileMetadata(relative_path=rel, sha256=file_hash, size_bytes=len(payload)))
            text = payload.decode("utf-8", "replace")
            framework_indicators.update(_find_terms(text, _FRAMEWORK_TERMS))
            auth_indicators.update(_find_terms(text, _AUTH_TERMS))
            routes.extend(_extract_routes(rel, text, file_hash))
    return _build_result(
        source_kind="zip",
        source_reference=path.name,
        selected=selected,
        routes=routes,
        framework_indicators=framework_indicators,
        auth_indicators=auth_indicators,
        ignored=ignored,
        warnings=warnings,
    )


def _validate_zip_member(info: zipfile.ZipInfo) -> str | None:
    path = PurePosixPath(info.filename)
    if info.is_dir():
        return None
    if path.is_absolute() or ".." in path.parts:
        raise OSMAPSourceReviewError("zip archive contains unsafe path traversal")
    mode = info.external_attr >> 16
    if stat.S_ISLNK(mode):
        raise OSMAPSourceReviewError("zip archive contains unsafe symlink")
    return path.as_posix()


def _build_result(
    *,
    source_kind: str,
    source_reference: str,
    selected: Iterable[SourceFileMetadata],
    routes: Iterable[SourceRouteCandidate],
    framework_indicators: Iterable[str],
    auth_indicators: Iterable[str],
    ignored: dict[str, str],
    warnings: list[str],
) -> SourceReviewResult:
    selected_tuple = tuple(selected)
    root_hasher = hashlib.sha256()
    for item in selected_tuple:
        root_hasher.update(f"{item.relative_path}:{item.sha256}\n".encode("utf-8"))
    return SourceReviewResult(
        source_kind=source_kind,
        source_reference=source_reference,
        source_root_hash=root_hasher.hexdigest(),
        file_count=len(selected_tuple),
        selected_files=selected_tuple,
        route_candidates=tuple(routes),
        framework_indicators=tuple(sorted(set(framework_indicators))),
        auth_indicators=tuple(sorted(set(auth_indicators))),
        ignored_file_reasons=dict(sorted(ignored.items())),
        warnings=tuple(warnings),
    )


def _extract_routes(relative_path: str, text: str, file_hash: str) -> list[SourceRouteCandidate]:
    candidates: list[SourceRouteCandidate] = []
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        for pattern in _ROUTE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            method = match.group(1).upper()
            path = match.group(2)
            if method == "ROUTE":
                method_values = _methods_from_line(line) or ("GET",)
            else:
                method_values = (method,)
            context = "\n".join(lines[max(0, index - 6): min(len(lines), index + 8)])
            hints = tuple(sorted(_find_terms(context, _AUTH_TERMS)))
            for resolved_method in method_values:
                candidates.append(
                    SourceRouteCandidate(
                        method=resolved_method,
                        path_pattern=path,
                        source_reference=relative_path,
                        handler_reference=f"{relative_path}:L{index}",
                        evidence_sha256=file_hash,
                        auth_hints=hints,
                        confidence="medium" if hints else "low",
                    )
                )
    return candidates


def _methods_from_line(line: str) -> tuple[str, ...]:
    match = _METHODS_PATTERN.search(line)
    if not match:
        return ()
    return tuple(item.strip(" '\"\t").upper() for item in match.group(1).split(",") if item.strip())


def _find_terms(text: str, terms: dict[str, str]) -> set[str]:
    lowered = text.lower()
    found: set[str] = set()
    for needle, label in terms.items():
        if needle in lowered:
            found.add(label)
    return found
