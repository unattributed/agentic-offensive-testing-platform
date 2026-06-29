"""Provenance-controlled registry for external YAML and YARA bundles."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .config import (
    ConfigError,
    require_bool,
    require_list,
    require_mapping,
    require_text,
    require_text_list,
)


SOURCE_KINDS = {"nuclei_yaml", "zap_automation_yaml", "yara"}
MANDATORY_DENIALS = {
    "code_execution",
    "credential_attack",
    "destructive_payload",
    "target_discovery",
}


@dataclass(frozen=True)
class TemplateSource:
    source_id: str
    kind: str
    repository: str
    commit_sha: str
    license_spdx: str
    license_reviewed: bool
    enabled: bool
    local_path: str
    sha256: str
    signature_required: bool
    allowed_template_ids: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    denied_capabilities: tuple[str, ...]


def _sha256_valid(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _github_repository(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and len([part for part in parsed.path.split("/") if part]) == 2
    )


def parse_template_registry(data: dict[str, Any]) -> dict[str, TemplateSource]:
    schema_version = require_text(data.get("schema_version"), "schema_version")
    if schema_version != "1.0":
        raise ConfigError(f"unsupported template registry schema_version: {schema_version}")
    raw_sources = require_list(data.get("sources"), "sources")
    sources: dict[str, TemplateSource] = {}
    allowed_fields = {
        "source_id",
        "kind",
        "repository",
        "commit_sha",
        "license_spdx",
        "license_reviewed",
        "enabled",
        "local_path",
        "sha256",
        "signature_required",
        "allowed_template_ids",
        "allowed_capabilities",
        "denied_capabilities",
    }
    for index, raw_source in enumerate(raw_sources):
        field = f"sources[{index}]"
        source = require_mapping(raw_source, field)
        unknown = sorted(set(source) - allowed_fields)
        if unknown:
            raise ConfigError(f"{field} contains unknown fields: {', '.join(unknown)}")
        source_id = require_text(source.get("source_id"), f"{field}.source_id")
        if source_id in sources:
            raise ConfigError(f"duplicate template source_id: {source_id}")
        kind = require_text(source.get("kind"), f"{field}.kind")
        if kind not in SOURCE_KINDS:
            raise ConfigError(f"{field}.kind is unsupported: {kind}")
        repository = require_text(source.get("repository"), f"{field}.repository")
        if not _github_repository(repository):
            raise ConfigError(f"{field}.repository must be a canonical HTTPS GitHub repository URL")
        commit_sha = require_text(source.get("commit_sha"), f"{field}.commit_sha")
        if len(commit_sha) != 40 or any(character not in "0123456789abcdef" for character in commit_sha):
            raise ConfigError(f"{field}.commit_sha must be a full lowercase Git commit SHA")
        digest = require_text(source.get("sha256"), f"{field}.sha256")
        if not _sha256_valid(digest):
            raise ConfigError(f"{field}.sha256 must be a lowercase SHA256 digest")
        local_path = require_text(source.get("local_path"), f"{field}.local_path")
        candidate_path = Path(local_path)
        if candidate_path.is_absolute() or ".." in candidate_path.parts:
            raise ConfigError(f"{field}.local_path must stay within the registry directory")
        allowed_ids = require_text_list(
            source.get("allowed_template_ids"),
            f"{field}.allowed_template_ids",
            allow_empty=False,
        )
        allowed_capabilities = require_text_list(
            source.get("allowed_capabilities"),
            f"{field}.allowed_capabilities",
            allow_empty=False,
        )
        denied_capabilities = require_text_list(
            source.get("denied_capabilities"),
            f"{field}.denied_capabilities",
            allow_empty=False,
        )
        missing_denials = sorted(MANDATORY_DENIALS - set(denied_capabilities))
        if missing_denials:
            raise ConfigError(f"{field} is missing mandatory denials: {', '.join(missing_denials)}")
        sources[source_id] = TemplateSource(
            source_id=source_id,
            kind=kind,
            repository=repository,
            commit_sha=commit_sha,
            license_spdx=require_text(source.get("license_spdx"), f"{field}.license_spdx"),
            license_reviewed=require_bool(source.get("license_reviewed"), f"{field}.license_reviewed"),
            enabled=require_bool(source.get("enabled"), f"{field}.enabled"),
            local_path=local_path,
            sha256=digest,
            signature_required=require_bool(
                source.get("signature_required"),
                f"{field}.signature_required",
            ),
            allowed_template_ids=tuple(allowed_ids),
            allowed_capabilities=tuple(allowed_capabilities),
            denied_capabilities=tuple(denied_capabilities),
        )
    return sources


def hash_template_bundle(path: str | Path) -> str:
    bundle = Path(path)
    if bundle.is_file():
        return hashlib.sha256(bundle.read_bytes()).hexdigest()
    if not bundle.is_dir():
        raise ConfigError(f"template bundle does not exist: {bundle}")
    digest = hashlib.sha256()
    files = sorted(item for item in bundle.rglob("*") if item.is_file())
    if not files:
        raise ConfigError(f"template bundle directory is empty: {bundle}")
    for item in files:
        relative = item.relative_to(bundle).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        content = item.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def verify_template_source(source: TemplateSource, registry_path: str | Path) -> list[str]:
    failures: list[str] = []
    if not source.enabled:
        failures.append("template source is disabled")
    if not source.license_reviewed:
        failures.append("template source license has not been reviewed")
    bundle = Path(registry_path).resolve().parent / source.local_path
    try:
        actual = hash_template_bundle(bundle)
    except (ConfigError, OSError) as exc:
        failures.append(str(exc))
    else:
        if actual != source.sha256:
            failures.append("template bundle SHA256 does not match registry")
    if source.kind == "nuclei_yaml" and not source.signature_required:
        failures.append("Nuclei template sources must require signatures")
    return failures
