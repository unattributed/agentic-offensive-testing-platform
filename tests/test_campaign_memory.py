from aotp.campaign_memory import CampaignMemoryEntry


def test_private_memory_schema_tracks_duplicate_fields():
    entry = CampaignMemoryEntry("program", "asset", "headers", "2026-01-01", ["fingerprint"], "none", "hash", "none", "")
    assert entry.finding_fingerprints == ["fingerprint"]
