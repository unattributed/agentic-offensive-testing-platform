from __future__ import annotations

import os
import subprocess

import pytest

from aotp.campaign_memory import (
    CampaignMemoryEntry,
    duplicate_fingerprints,
    finding_fingerprint,
    load_campaign_memory,
    write_campaign_memory,
)


def _entry() -> CampaignMemoryEntry:
    evidence_hash = "a" * 64
    return CampaignMemoryEntry(
        program_alias="program-one",
        asset_alias="asset-one",
        test_type="security-headers",
        date_tested="2026-07-01",
        finding_fingerprints=(
            finding_fingerprint(
                test_type="security-headers", evidence_hash=evidence_hash
            ),
        ),
        payload_family="none",
        evidence_hash=evidence_hash,
        report_outcome="not_reported",
        duplicate_status="no_match",
    )


def test_private_memory_round_trip_and_duplicate_match(tmp_path):
    entry = _entry()
    path = write_campaign_memory([entry], tmp_path / "campaign-memory.json")

    loaded = load_campaign_memory(path)

    assert loaded == (entry,)
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert duplicate_fingerprints(
        loaded,
        asset_alias="asset-one",
        test_type="security-headers",
        fingerprints=entry.finding_fingerprints,
    ) == entry.finding_fingerprints
    assert (
        duplicate_fingerprints(
            loaded,
            asset_alias="different-asset",
            test_type="security-headers",
            fingerprints=entry.finding_fingerprints,
        )
        == ()
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("asset_alias", "https://target.invalid", "must be an alias"),
        ("asset_alias", "target alias", "must be an alias"),
        ("finding_fingerprints", ("not-a-hash",), "must be SHA256"),
        ("evidence_hash", "not-a-hash", "must be a SHA256"),
        ("report_outcome", "auto_submitted", "unsupported"),
    ),
)
def test_campaign_memory_rejects_non_alias_or_unverified_values(
    field, value, message
):
    values = dict(_entry().__dict__)
    values[field] = value
    with pytest.raises(ValueError, match=message):
        CampaignMemoryEntry(**values).validate()


def test_campaign_memory_paths_are_repository_ignored(project_root):
    completed = subprocess.run(
        ["git", "check-ignore", "campaign-memory-private.json"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
