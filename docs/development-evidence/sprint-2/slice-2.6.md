# Slice 2.6 evidence: hash-chained event log

## Functional result

Campaign events are appended to a private JSONL log with contiguous sequence numbers, unique event IDs, previous-event hashes, and canonical event hashes. State retains the final hash and event count, so modification, deletion, reordering, state divergence, and broken resume continuity are detectable.

Events cover campaign start, objective result, policy or budget stop, human pause, review decision, resume, operator stop, and completion. A fresh campaign refuses to overwrite an existing checkpoint or event log.

## Validation

```bash
python3 -m pytest tests/test_campaign_events.py tests/test_campaign_control.py tests/test_campaign_loop.py tests/test_campaign_state.py tests/test_cli.py
```

```text
20 passed in 0.16s
```

Tests verify a complete chain, state-to-log consistency, expected event types, review and resume continuity, and detection of a modified historical outcome.
