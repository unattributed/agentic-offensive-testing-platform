"""Verified evidence and finding candidate Markdown reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import load_manifest, verify_evidence_directory
from .finding_candidate import load_candidate
from .panel_evidence import validate_panel_evidence_record
from .sbom_review import validate_sbom_record
from .crypto_review import validate_crypto_record
from .report_review import manifest_requires_report_review, report_inclusion_allowed


def _text(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _render_evidence(
    data: dict[str, Any],
    panel_record: dict[str, Any] | None = None,
    sbom_record: dict[str, Any] | None = None,
    crypto_record: dict[str, Any] | None = None,
) -> str:
    mappings = data.get("wstg_mapping") or data.get("artifact_mapping") or []
    lines = [
        f"### Case `{_text(data.get('case_id', 'unknown'))}`",
        "",
        f"- Verdict: `{_text(data.get('verifier_verdict', 'unknown'))}`",
        f"- Target alias: `{_text(data.get('target_alias', 'unknown'))}`",
        f"- Module: `{_text(data.get('module_name') or 'not recorded')}`",
        f"- Tool: `{_text(data.get('tool', 'unknown'))}`",
        f"- Confidence: `{_text(data.get('confidence', 'unknown'))}`",
        f"- Evidence mappings: `{_text(', '.join(mappings) if mappings else 'none recorded')}`",
        f"- Redaction: `{_text(data.get('redaction_status', 'unknown'))}`",
        f"- Manifest SHA256: `{_text(data.get('manifest_sha256', 'unknown'))}`",
    ]
    if panel_record is not None:
        lines.extend(
            [
                "",
                "#### Captured service control panel fields",
                "",
                f"- Panel alias: `{_text(panel_record['panel_alias'])}`",
                f"- Panel type: `{_text(panel_record['panel_type'])}`",
                f"- Network silent: `{panel_record['network_silent']}`",
                f"- Request count: `{panel_record['request_count']}`",
                "- Planned observations: `"
                + _text(", ".join(panel_record["planned_observations"]))
                + "`",
                f"- Evidence status: `{_text(panel_record['report_inclusion_status'])}`",
            ]
        )
    if sbom_record is not None:
        lines.extend(["", "#### Recorded SBOM components", ""])
        for component in sbom_record["components"]:
            lines.extend(
                [
                    f"- `{_text(component['name'])}` version `{_text(component['version'])}`",
                    f"  - Presence: `{component['presence']}`",
                    f"  - Reachability: `{component['reachability']}`",
                    f"  - Exploitability: `{component['exploitability']}`",
                    f"  - Source SHA256: `{component['source_artifact_sha256']}`",
                ]
            )
        lines.extend(["", sbom_record["caveat"]])
    if crypto_record is not None:
        tls = crypto_record["tls_evidence"]
        lines.extend(
            [
                "",
                "#### Recorded cryptographic controls",
                "",
                f"- TLS protocol: `{_text(tls.get('protocol'))}`",
                f"- Certificate signature algorithm: `{_text(tls.get('signature_algorithm'))}`",
                f"- Cookie attribute records: `{len(crypto_record['cookie_attributes'])}`",
                f"- Token algorithm setting: `{_text(crypto_record['token_configuration'].get('algorithm'))}`",
                f"- Weak algorithm indicators: `{len(crypto_record['weak_algorithm_indicators'])}`",
                f"- Private material: `{crypto_record['private_material']}`",
                "",
                crypto_record["caveat"],
            ]
        )
    return "\n".join(lines)


def _render_candidate(candidate) -> str:
    return "\n".join(
        [
            f"## {_text(candidate.title)}",
            "",
            f"- Finding ID: `{_text(candidate.finding_id)}`",
            f"- State: `{candidate.state}`",
            f"- Target alias: `{_text(candidate.target_alias)}`",
            f"- Case ID: `{_text(candidate.case_id)}`",
            f"- Severity candidate: `{candidate.severity_candidate}`",
            f"- Confidence: `{candidate.confidence}`",
            f"- Evidence strength: `{candidate.evidence_strength}`",
            f"- Report review required: `{candidate.report_review_required}`",
            f"- Report review status: `{_text(candidate.report_review_status)}`",
            f"- Report reviewer: `{_text(candidate.report_reviewer)}`",
            f"- Report review SHA256: `{_text(candidate.report_review_sha256)}`",
            f"- Evidence manifest SHA256: `{candidate.evidence_manifest_sha256}`",
            f"- Fingerprint: `{candidate.fingerprint}`",
            "",
            "### Recorded summary",
            "",
            _text(candidate.summary),
        ]
    )


def generate_markdown(
    evidence_directory: str | Path,
    findings_directory: str | Path | None = None,
) -> str:
    evidence_root = Path(evidence_directory)
    failures = verify_evidence_directory(evidence_root)
    if failures:
        raise ValueError("evidence verification failed: " + "; ".join(failures))
    manifest_entries = [
        (path, load_manifest(path))
        for path in sorted(evidence_root.rglob("evidence.json"))
    ]
    manifests_by_hash = {
        manifest.manifest_sha256: (path, manifest)
        for path, manifest in manifest_entries
    }
    panel_records: dict[str, dict[str, Any]] = {}
    sbom_records: dict[str, dict[str, Any]] = {}
    crypto_records: dict[str, dict[str, Any]] = {}
    for manifest_path, manifest in manifest_entries:
        if not manifest_requires_report_review(manifest):
            continue
        artifacts = [
            artifact
            for artifact in manifest.artifacts
            if artifact.get("role") == "service_control_panel_evidence_record"
        ]
        has_observation_plan = isinstance(
            manifest.response_metadata.get("observation_plan"), dict
        )
        if has_observation_plan and len(artifacts) != 1:
            raise ValueError(
                f"panel evidence {manifest.case_id} requires exactly one panel evidence record"
            )
        if not artifacts:
            continue
        if len(artifacts) != 1:
            raise ValueError(
                f"panel evidence {manifest.case_id} has duplicate panel evidence records"
            )
        artifact_path = manifest_path.parent / artifacts[0]["redacted_path"]
        try:
            record = json.loads(artifact_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"panel evidence record is invalid: {artifact_path}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"panel evidence record is invalid: {artifact_path}")
        validate_panel_evidence_record(record)
        if (
            record["case_id"] != manifest.case_id
            or record["target_alias"] != manifest.target_alias
        ):
            raise ValueError("panel evidence record does not match its manifest")
        panel_records[manifest.manifest_sha256 or ""] = record
    for manifest_path, manifest in manifest_entries:
        artifacts = [
            artifact
            for artifact in manifest.artifacts
            if artifact.get("role") == "sbom_component_evidence"
        ]
        if not artifacts:
            continue
        if len(artifacts) != 1:
            raise ValueError("SBOM evidence requires exactly one component record")
        record = json.loads(
            (manifest_path.parent / artifacts[0]["redacted_path"]).read_text(
                encoding="utf-8"
            )
        )
        validate_sbom_record(record)
        if record["artifact_alias"] != manifest.sbom_artifact:
            raise ValueError("SBOM evidence record does not match its manifest")
        sbom_records[manifest.manifest_sha256 or ""] = record
    for manifest_path, manifest in manifest_entries:
        artifacts = [
            artifact
            for artifact in manifest.artifacts
            if artifact.get("role") == "cryptographic_controls_evidence"
        ]
        if not artifacts:
            continue
        record = json.loads(
            (manifest_path.parent / artifacts[0]["redacted_path"]).read_text(
                encoding="utf-8"
            )
        )
        validate_crypto_record(record)
        crypto_records[manifest.manifest_sha256 or ""] = record

    ready_candidates = []
    excluded_count = 0
    if findings_directory is not None:
        for path in sorted(Path(findings_directory).rglob("*.json")):
            candidate = load_candidate(path)
            matched = manifests_by_hash.get(candidate.evidence_manifest_sha256)
            if matched is None:
                raise ValueError(
                    f"finding {candidate.finding_id} references evidence outside the report set"
                )
            _, manifest = matched
            sbom_risk_allowed = (
                manifest.module_name != "sbom_review"
                or (
                    candidate.component_presence_only
                    and candidate.reachability_status == "verified"
                    and candidate.exploitability_status == "verified"
                )
            )
            crypto_record = crypto_records.get(manifest.manifest_sha256 or "", {})
            crypto_risk_allowed = (
                manifest.module_name != "crypto_controls"
                or not crypto_record.get("weak_algorithm_indicators")
                or (
                    candidate.crypto_indicator_only
                    and candidate.crypto_indicator_status == "verified_weakness"
                )
            )
            if (
                candidate.state == "ready_for_report"
                and report_inclusion_allowed(candidate, manifest)
                and sbom_risk_allowed
                and crypto_risk_allowed
            ):
                ready_candidates.append(candidate)
            else:
                excluded_count += 1

    lines = [
        "# AOTP human-review draft",
        "",
        "This draft is generated only from integrity-verified evidence and report-ready finding candidates. It does not infer vulnerabilities, impact, exploitability, affected assets, or remediation.",
        "",
        f"Verified evidence records: `{len(manifest_entries)}`",
        f"Report-ready findings: `{len(ready_candidates)}`",
        f"Excluded non-ready candidates: `{excluded_count}`",
        "",
    ]
    if ready_candidates:
        lines.extend(_render_candidate(candidate) + "\n" for candidate in ready_candidates)
    else:
        lines.extend(
            [
                "## Finding candidates",
                "",
                "No evidence-bound candidate has completed human review for report inclusion.",
                "",
            ]
        )
    lines.extend(["## Evidence appendix", ""])
    lines.extend(
        _render_evidence(
            asdict_manifest(manifest),
            panel_records.get(manifest.manifest_sha256 or ""),
            sbom_records.get(manifest.manifest_sha256 or ""),
            crypto_records.get(manifest.manifest_sha256 or ""),
        )
        + "\n"
        for _, manifest in manifest_entries
    )
    return "\n".join(lines).rstrip() + "\n"


def asdict_manifest(manifest) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(manifest)
