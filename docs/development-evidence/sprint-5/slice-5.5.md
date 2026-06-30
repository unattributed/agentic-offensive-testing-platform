# Sprint 5 Slice 5.5: lockout stops and campaign integration

## Implemented behavior

Service control panel objectives can now run through the campaign engine with explicit panel
aliases, panel types, safe observations, and artifact mappings. A panel campaign must declare the
`authentication_lockout_risk` stop condition.

An objective carrying `lockout_risk_detected: true` pauses before execution. The campaign writes
a zero-request evidence manifest and a `campaign_paused` event that identify the stop condition.
Resumption requires a human review decision bound to the exact campaign checkpoint.

Completed panel campaign objectives write `panel-evidence.json`, register its hash in the evidence
manifest, and remain network-silent.

## Safety properties

- Category and module mismatches are denied.
- Configured panel denials override approvals.
- Known unsafe actions cannot be approved in panel scope.
- Safe observation planning requires an explicit non-empty observation list.
- Lockout risk pauses before execution with zero requests.
- Campaign review decisions bind to the exact state SHA256.

## Validation

- `python -m pytest tests/test_control_panel_campaign.py`
- `python -m pytest tests/test_control_panel_targets.py`
- `python -m pytest tests/test_control_panel_safe_observations.py`
- Full compile, test, and repository safety gates.

## No private material

All fixtures use reserved aliases and network-silent dry-run behavior. No private target,
credential, screenshot, capture, finding, report, or live evidence is committed.
