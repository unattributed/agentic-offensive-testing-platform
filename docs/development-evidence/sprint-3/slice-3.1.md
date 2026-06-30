# Slice 3.1 evidence: evidence manifest contract

Evidence manifests now validate schema, identity, UTC timestamps, verdict, confidence, execution mode, request counts, report status, artifact paths, hashes, and redaction. Each manifest carries a canonical SHA256 over its content.

Writes are atomic, file mode `0600`, and directory mode `0700`. Loading verifies integrity before returning data.

```text
python3 -m pytest tests/test_evidence_manifest.py tests/test_campaign_loop.py tests/test_langgraph_orchestration.py
14 passed in 0.31s
```

Tests prove campaign compatibility, round-trip integrity, private permissions, required-field validation, and detection of a changed case identifier.
