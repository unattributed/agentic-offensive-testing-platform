# Slice 3.3 evidence: artifact hashing

Evidence can now register local artifacts with stable ID, role, media type, relative raw and redacted paths, size, hashes, and redaction status. Registration refuses paths outside the evidence directory, symlinks, duplicates, and malformed digests.

Verification detects changed size, raw content, redacted content, missing files, and path escape.

```text
python3 -m pytest tests/test_evidence_manifest.py
6 passed in 0.02s
```
