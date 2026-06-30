# Slice 2.2 evidence: campaign state model

## Functional result

Campaign checkpoints now use a versioned state envelope with a canonical SHA256 integrity digest. State validation covers campaign and scope hashes, statuses, timezone-aware timestamps, revisions, iteration and elapsed-time values, objective disposition exclusivity, counters, completion invariants, and event-chain metadata.

Writes use a same-directory temporary file, `fsync`, atomic replacement, and mode `0600`.

## Validation

```bash
python3 -m pytest tests/test_campaign_state.py tests/test_campaign_loop.py tests/test_cli.py
```

```text
10 passed in 0.08s
```

Tests prove round-trip persistence, revision increment, private permissions, tamper detection, disposition-overlap rejection, invalid-completion rejection, and compatibility with real dry-run campaign state.
