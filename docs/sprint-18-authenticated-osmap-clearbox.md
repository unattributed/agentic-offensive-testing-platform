# Sprint 18 authenticated OSMAP and clearbox workflow

## Goal

Sprint 18 adds authenticated, metadata-safe, source-informed OSMAP clearbox testing for owned or explicitly authorized targets. It introduces interactive credential and TOTP collection, authenticated session boundaries, session material evidence routing, local-only OSMAP source review, route and authentication maps, WSTG candidate generation, governed authenticated execution, logout verification, agentic candidate review, and manual campaign package assembly.

## Relationship to Sprint 17F

Sprint 18 consumes the Sprint 17 follow-up WSTG execution adapter contract in `src/aotp/wstg/execution_adapter.py`. It does not create a parallel execution path. OSMAP route hints are converted into `WSTGObjective` values and then into `WSTGExecutionRequest` objects with `WSTGAdapterKind.APP_SPECIFIC_RUNNER`. Results return as `WSTGExecutionResult` with redacted `WSTGRedactedEvidenceArtifact` references. Candidate findings are created only from failed adapter results with supporting evidence.

## Authenticated testing safety boundary

`src/aotp/auth_session.py` defines `AuthenticatedSessionBoundary`, `AllowedRoute`, authenticated route decisions, and logout boundary records. The boundary binds campaign id, operator alias, target alias, account alias, authorization reference, approval reference, ROE reference, exact scope digest, approval digest, expiry, permissions, allowed routes, allowed auth states, storage policy, and evidence classification.

The boundary fails closed when approval is missing, expired, not bound to the scope digest, not bound to the operator, missing `authenticated_testing`, crossing target or account alias, crossing route scope, or using an unauthorized auth state.

## Credential and TOTP handling

`src/aotp/credential_prompt.py` adds `SecretInput`, `CredentialBundle`, and `collect_credentials`. Password and TOTP values are collected through a secret prompt function, not argv. Their string and repr forms are redacted, public serialization contains only hashes or metadata, and callers can clear in-memory secret wrappers after use.

## Session material classification and routing

`src/aotp/csrf.py` and `src/aotp/session_evidence.py` classify cookies, CSRF values, bearer tokens, session identifiers, login markers, logout markers, and post-logout checks. Storage routes are:

* `vaulted`
* `memory_only`
* `do_not_store`
* `public_metadata_only`

Normal evidence contains only aliases, classifications, source labels, hashes, vault handles, and redaction status. Raw cookies, CSRF values, bearer tokens, passwords, TOTP values, and session identifiers are excluded from normal evidence.

## OSMAP source review boundary

`src/aotp/integrations/osmap_source_review.py` accepts only local repository paths or local zip archives. It rejects remote URLs, path traversal, symlinks, unreadable or unsupported sources, and unsupported archive paths. It never imports, executes, clones, or vendors reviewed code. It emits source kind, source root hash, selected file hashes, route candidates, framework indicators, auth indicators, ignored file reasons, and warnings.

## Route and auth map schema

`src/aotp/integrations/osmap_route_map.py` converts safe source metadata into deterministic route and auth maps. Each route records route id, method, path pattern, handler reference, auth-required hint, mechanism hint, source reference, confidence, hash references, and limitations. Source hints are not findings.

## WSTG candidate generation flow

`src/aotp/integrations/osmap_wstg_mapper.py` maps route and auth hints into Sprint 17F adapter requests. The mapper requires authenticated WSTG scope, session material permission, AUTH phase allowance, approval reference, and approved executable families. Hints never grant execution authority.

## Governed authenticated execution flow

`src/aotp/agent_tools/osmap_authenticated_wstg.py` defines `AuthenticatedOSMAPWSTGRunner`. The runner accepts only `APP_SPECIFIC_RUNNER` requests for `osmap_authenticated_wstg`, requires an active session boundary, checks route scope, denies raw secret metadata, enforces request budget, and supports network-silent synthetic observations for tests. Live-capable execution remains disabled unless explicit live and operator approval controls are supplied by the caller.

## Logout and post-logout verification flow

Logout support records a cleanup event and post-logout check status as `blocked`, `still_authenticated`, `inconclusive`, `skipped`, or `denied`. Logout records never store invalidated raw session material.

## Candidate finding review rules

Agentic candidate review is false-positive-safe. Source hints, route hints, auth hints, pass results, warning results, skipped checks, and inconclusive checks do not create findings. Failed authenticated checks may create a candidate only when the Sprint 17F adapter result contains redacted evidence. Candidates remain `candidate_needs_human_validation` and cannot become report-ready without human validation through the existing lifecycle.

## Campaign package output

The package builder emits scope aliases, authorization references, route and auth map summaries, WSTG candidates, executed check summaries, logout summary, candidate finding references, limitations, `no_secret_confirmation`, and `manual_review_only`. Vault material and raw session values remain outside the package.

## Validation commands

Recommended Sprint 18 validation:

```sh
python3 -m compileall src tests
python3 -m pytest tests/test_credential_prompt.py tests/test_auth_session.py tests/test_session_evidence_redaction.py tests/test_osmap_source_review.py tests/test_osmap_route_map.py tests/test_osmap_wstg_mapper.py tests/test_osmap_authenticated_wstg.py
python3 -m pytest tests/test_wstg_execution_adapter.py
python3 -m pytest
./scripts/validate-repository-safety.sh
make test
```

Run `make check` as well if it is available in the checked-out repository.

## Limitations and deferred work

This sprint does not implement automatic login form driving, browser session capture, public target crawling, account lifecycle management, bug bounty submission, exploit automation, brute force, MFA bypass, or destructive administration. It creates the governed boundaries, metadata flow, adapter compatibility, and synthetic test path needed before any later live authenticated adapter can be safely introduced.

## Repository safety confirmation

The implementation is designed so private targets, credentials, cookies, CSRF values, bearer tokens, session identifiers, TOTP values, screenshots, traces, live reports, and generated evidence are not committed. Tests use synthetic local fixtures only.
