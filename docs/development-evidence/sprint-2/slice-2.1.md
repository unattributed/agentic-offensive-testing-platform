# Slice 2.1 evidence: strict campaign parser

## Functional result

Campaign YAML is now a validated execution contract with schema version, description, hard limits, dry-run default, mandatory stop behavior, supported modules, unique objectives, typed priorities, explicit dependencies, approval classification, and module parameters.

The parser rejects unknown fields, live-by-default campaigns, unsupported modules or stops, duplicate identifiers, missing dependencies, self-dependencies, and dependency cycles before scheduling.

## Validation

```bash
python3 -m pytest tests/test_campaign.py tests/test_campaign_loop.py tests/test_cli.py
```

```text
14 passed in 0.09s
```

All three example campaigns parse without mutation. Negative tests exercise duplicate IDs, unknown dependencies, cycles, unknown fields, and unsafe default execution mode.
