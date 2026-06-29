"""Evidence-only Markdown reporting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _render_record(data: dict[str, Any]) -> str:
    mappings = data.get("wstg_mapping") or data.get("artifact_mapping") or []
    lines = [
        f"## Case `{data.get('case_id', 'unknown')}`",
        "",
        f"- Verdict: `{data.get('verifier_verdict', 'unknown')}`",
        f"- Target alias: `{data.get('target_alias', 'unknown')}`",
        f"- Module: `{data.get('module_name') or 'not recorded'}`",
        f"- Tool: `{data.get('tool', 'unknown')}`",
        f"- Confidence: `{data.get('confidence', 'unknown')}`",
        f"- Evidence mappings: `{', '.join(mappings) if mappings else 'none recorded'}`",
        f"- Redaction: `{data.get('redaction_status', 'unknown')}`",
        f"- Report status: `{data.get('report_inclusion_status', 'unknown')}`",
    ]
    return "\n".join(lines)


def generate_markdown(evidence_directory: str | Path) -> str:
    root = Path(evidence_directory)
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("evidence.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    lines = [
        "# AOTP evidence report",
        "",
        "This report contains recorded evidence fields only. It does not infer vulnerabilities, impact, exploitability, affected assets, or remediation.",
        "",
    ]
    if not records:
        lines.append("No evidence records were found.")
    else:
        lines.extend(_render_record(record) + "\n" for record in records)
    return "\n".join(lines).rstrip() + "\n"
