# Sprint 0 Slice 0.3

Initial commit `094e756` added the command-line entry point and fail-closed YAML loading. Current
configuration models reject missing, malformed, unknown, contradictory, and unsupported fields.

Current focused validation:

```text
python3 -m pytest -q tests/test_config.py tests/test_cli.py
15 passed
```

The example scope validates and the default dry-run remains network-silent.
