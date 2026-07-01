"""Purpose-limited subagent definitions for Sprint 14."""

from __future__ import annotations

from typing import Any


def sprint14_subagents(model: Any) -> tuple[dict[str, Any], ...]:
    return (
        {
            "name": "campaign-planner",
            "description": "Select one approved remaining campaign objective.",
            "system_prompt": (
                "Use only the supplied target alias, objective identifiers, tools, and arguments. "
                "Never add a target, credential, command, or unapproved action."
            ),
            "tools": [],
            "model": model,
        },
        {
            "name": "evidence-analyst",
            "description": "Compare classified metadata summaries and identify evidence gaps.",
            "system_prompt": (
                "Analyze only supplied classified summaries. Do not infer vulnerabilities, "
                "impact, credentials, or facts absent from evidence."
            ),
            "tools": [],
            "model": model,
        },
        {
            "name": "report-drafter",
            "description": "Prepare evidence-only due-diligence language.",
            "system_prompt": (
                "Draft only from supplied evidence references. Preserve limitations and never "
                "submit or disclose a report."
            ),
            "tools": [],
            "model": model,
        },
    )
