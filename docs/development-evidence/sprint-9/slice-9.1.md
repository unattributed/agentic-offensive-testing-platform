# Sprint 9 Slice 9.1

The local model configuration is strict and fail closed. It requires an unauthenticated loopback
HTTP endpoint with an explicit port, a default model from the configured allowlist, a timeout of
at most 30 seconds, structured JSON, recursive redaction, and remote endpoints disabled.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_model_config.py
10 passed
```

No model service was contacted. No private scope, target, secret, or evidence was committed.
