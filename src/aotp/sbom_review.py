"""Offline ingestion and evidence modeling for provided dependency artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .redaction import assert_value_redacted

SBOM_EVIDENCE_FILE = "sbom-evidence.json"
SBOM_RECORD_TYPE = "sbom_component_evidence"
VULNERABILITY_MAPPING_CONTRACT = {
    "mode": "configured_local_data_source_only",
    "network_lookup": False,
    "required_fields": ["source_alias", "source_version", "source_sha256"],
    "automatic_exploitability_claims": False,
}


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ingest_sbom_artifact(path: str | Path, artifact_alias: str) -> dict[str, Any]:
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("provided SBOM artifact must be a regular non-symlink file")
    if source.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("provided SBOM artifact exceeds the local size limit")
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("provided SBOM artifact is not valid JSON") from exc
    if not isinstance(document, dict) or not isinstance(document.get("components"), list):
        raise ValueError("provided SBOM artifact has no component inventory")
    artifact_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    components: list[dict[str, Any]] = []
    for index, raw in enumerate(document["components"]):
        if not isinstance(raw, dict):
            raise ValueError(f"SBOM component {index} is not a mapping")
        name = raw.get("name")
        version = raw.get("version")
        if not isinstance(name, str) or not name or not isinstance(version, str) or not version:
            raise ValueError(f"SBOM component {index} is missing name or version")
        components.append(
            {
                "name": name,
                "version": version,
                "package_url": raw.get("purl") if isinstance(raw.get("purl"), str) else None,
                "source_artifact": artifact_alias,
                "source_artifact_sha256": artifact_sha256,
                "component_sha256": _digest(raw),
                "presence": "observed",
                "reachability": "not_assessed",
                "exploitability": "not_assessed",
                "vulnerability_mappings": [],
            }
        )
    record = {
        "schema_version": "1.0",
        "record_type": SBOM_RECORD_TYPE,
        "artifact_alias": artifact_alias,
        "artifact_sha256": artifact_sha256,
        "component_count": len(components),
        "components": components,
        "vulnerability_mapping_contract": VULNERABILITY_MAPPING_CONTRACT,
        "network_silent": True,
        "request_count": 0,
        "caveat": "Component presence does not establish reachability or exploitability.",
    }
    validate_sbom_record(record)
    return record


def validate_sbom_record(record: dict[str, Any]) -> None:
    if record.get("record_type") != SBOM_RECORD_TYPE or record.get("schema_version") != "1.0":
        raise ValueError("unsupported SBOM evidence record")
    components = record.get("components")
    if not isinstance(components, list) or record.get("component_count") != len(components):
        raise ValueError("SBOM component count is invalid")
    if record.get("network_silent") is not True or record.get("request_count") != 0:
        raise ValueError("SBOM review must remain network silent")
    for component in components:
        if component.get("presence") != "observed":
            raise ValueError("SBOM component presence is invalid")
        if component.get("reachability") != "not_assessed":
            raise ValueError("SBOM reachability cannot be inferred")
        if component.get("exploitability") != "not_assessed":
            raise ValueError("SBOM exploitability cannot be inferred")
        if component.get("vulnerability_mappings") != []:
            raise ValueError("SBOM vulnerability mappings require a configured data source")
        if component.get("source_artifact") != record.get("artifact_alias"):
            raise ValueError("SBOM component source alias is invalid")
        if component.get("source_artifact_sha256") != record.get("artifact_sha256"):
            raise ValueError("SBOM component source hash is invalid")
        for field in ("source_artifact_sha256", "component_sha256"):
            digest = component.get(field)
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError(f"SBOM component {field} is invalid")
    assert_value_redacted(record)


def write_sbom_record(record: dict[str, Any], directory: str | Path) -> Path:
    validate_sbom_record(record)
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    path = output / SBOM_EVIDENCE_FILE
    descriptor, temporary_name = tempfile.mkstemp(prefix=".sbom-evidence.", dir=output)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path
