from __future__ import annotations

import json
import os

import pytest

from aotp.evidence import EvidenceManifest, write_manifest
from aotp.report_package import build_report_package, load_report_package


def _evidence(tmp_path):
    manifest = EvidenceManifest(
        run_id="package-run",
        timestamp_utc="2026-07-01T00:00:00+00:00",
        operator="operator-alias",
        sponsor_alias="sponsor-alias",
        target_alias="asset-alias",
        authorization_reference="authorization-reference",
        rules_of_engagement_reference="rules-reference",
        confidentiality_reference=None,
        case_id="case-alias",
        tool="network-silent-test",
        verifier_verdict="inconclusive",
        confidence="low",
    )
    path = write_manifest(manifest, tmp_path / "evidence")
    return path, manifest


def test_report_package_is_integrity_bound_pending_human_review(tmp_path):
    evidence_path, evidence = _evidence(tmp_path)
    draft = tmp_path / "source-report.md"
    draft.write_text("# Draft report\n\nAlias-only reviewed evidence.\n", encoding="utf-8")

    path = build_report_package(
        draft,
        [evidence_path],
        tmp_path / "package",
        package_id="package-one",
        created_at_utc="2026-07-01T00:00:00Z",
    )
    package = load_report_package(path)

    assert package.status == "draft"
    assert package.human_review_required is True
    assert package.review_status == "pending_human_review"
    assert package.submission_mode == "manual_only"
    assert package.evidence_manifest_sha256 == (evidence.manifest_sha256,)
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert os.stat(path.parent / "draft-report.md").st_mode & 0o777 == 0o600


def test_report_package_rejects_modified_draft(tmp_path):
    evidence_path, _ = _evidence(tmp_path)
    draft = tmp_path / "source-report.md"
    draft.write_text("# Draft report\n", encoding="utf-8")
    path = build_report_package(
        draft,
        [evidence_path],
        tmp_path / "package",
        package_id="package-one",
    )
    (path.parent / "draft-report.md").write_text("modified", encoding="utf-8")

    with pytest.raises(ValueError, match="bundled draft integrity"):
        load_report_package(path)


def test_report_package_rejects_secret_bearing_draft(tmp_path):
    evidence_path, _ = _evidence(tmp_path)
    draft = tmp_path / "source-report.md"
    draft.write_text(
        "# Draft report\n\nAuthorization: " + "Bearer " + "abcdefghijklmnop\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="redaction check failed"):
        build_report_package(
            draft,
            [evidence_path],
            tmp_path / "package",
            package_id="package-one",
        )


def test_report_package_rejects_modified_manifest(tmp_path):
    evidence_path, _ = _evidence(tmp_path)
    draft = tmp_path / "source-report.md"
    draft.write_text("# Draft report\n", encoding="utf-8")
    path = build_report_package(
        draft,
        [evidence_path],
        tmp_path / "package",
        package_id="package-one",
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "ready"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="human-reviewed manual draft"):
        load_report_package(path)
