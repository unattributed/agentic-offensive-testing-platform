# Sprint 9 Slice 9.6

Adversarial prompt tests prove that bearer values, cookies, session identifiers, private keys,
email addresses, API keys, access keys, JWTs, and semantic secret fields do not reach the
serialized request body, including when nested in mappings, lists, or tuples.

Unsupported objects, sets, non-finite numbers, and oversized prompts fail before the transport is
called. Secret-bearing or non-finite structured responses fail closed.

Focused validation:

```text
./.venv/bin/python -m pytest -q tests/test_ollama_prompt_safety.py
10 passed
```

Every transport was an in-memory stub. No model service or target was contacted.
