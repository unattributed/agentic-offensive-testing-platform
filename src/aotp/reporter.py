"""Verified evidence and finding candidate Markdown reporting."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence import load_manifest, verify_evidence_directory
from .finding_candidate import load_candidate
from .report_review import report_inclusion_allowed


def _text(value: Any) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def _render_evidence(data: dict[str, Any]) -> str:
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
    manifests = [
        load_manifest(path)
        for path in sorted(evidence_root.rglob("evidence.json"))
    ]
    manifest_hashes = {manifest.manifest_sha256 for manifest in manifests}

    ready_candidates = []
    excluded_count = 0
    if findings_directory is not None:
        for path in sorted(Path(findings_directory).rglob("*.json")):
            candidate = load_candidate(path)
            if candidate.evidence_manifest_sha256 not in manifest_hashes:
                raise ValueError(
                    f"finding {candidate.finding_id} references evidence outside the report set"
                )
            if candidate.state == "ready_for_report" and report_inclusion_allowed(candidate):
                ready_candidates.append(candidate)
            else:
                excluded_count += 1

    lines = [
        "# AOTP human-review draft",
        "",
        "This draft is generated only from integrity-verified evidence and report-ready finding candidates. It does not infer vulnerabilities, impact, exploitability, affected assets, or remediation.",
        "",
        f"Verified evidence records: `{len(manifests)}`",
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
    lines.extend(_render_evidence(asdict_manifest(manifest)) + "\n" for manifest in manifests)
    return "\n".join(lines).rstrip() + "\n"


def asdict_manifest(manifest) -> dict[str, Any]:
    from dataclasses import asdict

    return asdict(manifest)
