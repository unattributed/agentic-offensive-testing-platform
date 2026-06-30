# Sprint 5 Slice 5.1, control panel target model

## Implemented behavior

Slice 5.1 defines explicit management panel aliases in scope configuration and enforces them in
the policy gate for service control panel objectives. A panel objective must name a listed
`panel_alias`, must bind that alias to the expected `target_alias`, and must stay within the
network-silent dry-run boundary unless future live gates are added.

Panel types are constrained to:

- `admin_panel`
- `service_console`
- `monitoring_panel`
- `mail_admin_interface`
- `ci_cd_panel`
- `cloud_console_placeholder`
- `generic_management_interface`

## Safety boundary

The policy gate denies unlisted panel aliases, missing panel aliases, target mismatch, credential
guessing, default-password checks, brute force, login attempts, credential stuffing, password
spraying, token replay, session hijacking, lockout-triggering checks, destructive panel actions,
and unsafe crawling. Dry-run execution remains deterministic and sends zero network requests.

## Validation

Focused validation for this slice is:

```sh
python -m pytest tests/test_control_panel_targets.py
```

Full validation remains:

```sh
make PYTHON=.venv/bin/python compile
make PYTHON=.venv/bin/python test
make PYTHON=.venv/bin/python check
./scripts/validate-repository-safety.sh
```

## No private material

No private scope, target, credential, screenshot, finding, report, trace, generated capture,
campaign memory, or real evidence was committed.

## Deferred to Sprint 5.2

Sprint 5.2 should model safe panel observations such as headers, TLS metadata, login exposure,
version indicators, default pages, indexing, and unauthenticated metadata. It must not add login
attempts, credential guessing, brute force, or panel crawling without a separate explicit gate.
