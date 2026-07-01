"""Deterministic placeholder evidence and report generation for evaluator demos."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path

from .evidence import EvidenceManifest, write_manifest
from .reporter import generate_markdown


def generate_placeholder_report() -> str:
    manifest = EvidenceManifest(
        run_id="demo-placeholder-run",
        timestamp_utc="2026-01-01T00:00:00+00:00",
        operator="operator-placeholder",
        sponsor_alias="sponsor-placeholder",
        target_alias="local-placeholder",
        authorization_reference="example-only",
        rules_of_engagement_reference="example-only",
        confidentiality_reference=None,
        case_id="demo-placeholder-control",
        tool="deterministic-dry-run",
        verifier_verdict="inconclusive",
        confidence="not_assessed",
        campaign_id="demo-placeholder-campaign",
        campaign_iteration_id="0001",
        parent_test_objective="Demonstrate evidence-only reporting",
        module_name="wstg_webapp",
        wstg_mapping=["WSTG-CONF-14"],
        target_category="placeholder",
        execution_mode="dry_run",
        policy_decision="allowed placeholder dry run",
        request_count=0,
        response_metadata={
            "status": "placeholder metadata only; no network request was sent"
        },
    )
    with TemporaryDirectory(prefix="aotp-placeholder-report.") as directory:
        root = Path(directory)
        write_manifest(manifest, root)
        return generate_markdown(root)
