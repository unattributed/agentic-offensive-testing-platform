# Sprint 9 Slice 9.2

The local adapter sends non-streaming requests to the loopback generate endpoint with an explicit
JSON schema, deterministic temperature, a configured timeout, and a one MiB response bound. It
returns only the parsed schema-validated object.

Malformed envelopes, invalid JSON, unknown response fields, oversized responses, unavailable local
services, and unapproved models fail with bounded adapter errors. Tests use an injected in-memory
transport, so no service or target is contacted.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_ollama_adapter.py
8 passed
```

No private scope, target, secret, or evidence was committed.
