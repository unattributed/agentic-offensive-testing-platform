# Sprint 9 Slice 9.5

Prompt sanitization recursively covers mappings, lists, values, and mapping keys. It strips
authorization values, credentials, cookies, session identifiers, token classes, private key
material, access keys, email addresses, passwords, and nested secret fields before serialization.
Redaction finding paths never echo a secret-bearing mapping key.

The adapter rechecks both structured values and serialized prompt text before transport. It also
rejects secret-bearing model responses rather than passing them downstream.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_redaction.py tests/test_ollama_adapter.py
32 passed
```

Tests used only local in-memory data and transport stubs.
