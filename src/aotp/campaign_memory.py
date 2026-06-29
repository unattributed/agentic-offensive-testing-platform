"""Private local prior-testing memory schema."""

from dataclasses import dataclass


@dataclass
class CampaignMemoryEntry:
    program_alias: str
    asset_alias: str
    test_type: str
    date_tested: str
    finding_fingerprints: list[str]
    payload_family: str
    evidence_hash: str
    report_outcome: str
    duplicate_notes: str
