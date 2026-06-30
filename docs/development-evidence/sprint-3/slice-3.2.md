# Slice 3.2 evidence: structured redaction

Redaction now recursively inspects mappings, lists, field names, and text. Findings expose only field path, secret class, and SHA256, never the matched value. Sensitive fields and embedded patterns are sanitized before local-model use.

Coverage includes API keys, cookies, bearer and basic authorization, session IDs, private keys, passwords, GitHub tokens, JWTs, and email addresses. Reference, alias, status, and hash fields remain usable.

```text
python3 -m pytest tests/test_redaction.py tests/test_evidence_manifest.py tests/test_campaign_loop.py
20 passed in 0.07s
```
