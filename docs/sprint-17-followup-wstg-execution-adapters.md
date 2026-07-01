# Sprint 17 Follow-up: WSTG Execution Adapter Contract

This follow-up completes the Sprint 17 carry-forward requirement by adding an OSMAP-inspired execution adapter contract for generated WSTG objectives.

## Purpose

Sprint 17 created the reusable WSTG coverage and objective-selection foundation. This follow-up adds the missing bridge between generated objectives and evidence-producing execution layers.

The adapter contract converts a generated WSTG objective into one of two execution paths:

- governed native tool call
- application-specific runner call

The contract remains network-silent by itself. It records execution intent, result semantics, evidence references, coverage updates, and optional finding candidates only when redacted evidence supports them.

## Delivered

- `WSTGExecutionRequest`, a governed adapter request for one generated objective.
- `WSTGExecutionResult`, an OSMAP-style result with `pass`, `fail`, `warning`, `skip`, and `not_applicable` statuses.
- `WSTGRedactedEvidenceArtifact`, a reference-only evidence contract for redacted request, response, log, summary, and screenshot artifacts.
- `WSTGFindingCandidate`, an evidence-bound candidate emitted only from failed execution results.
- `coverage_record_from_execution_result`, a converter from execution result to Sprint 17 coverage record.
- `apply_execution_result_to_coverage`, a helper that records adapter results in the coverage ledger.
- focused adapter tests that validate request generation, redacted evidence constraints, result-to-coverage conversion, and finding-candidate gating.

## Safety model

The adapter contract does not perform live requests. Live behavior remains delegated to the governed tool registry or to app-specific runners that already enforce scope, ROE, budgets, approvals, redaction, and evidence handling.

The contract rejects:

- missing approval references
- live execution without a positive request budget
- absolute evidence paths
- evidence references that escape the evidence root
- unredacted evidence artifacts
- unsupported evidence classifications
- finding candidates from anything except failed results
- finding candidates that do not reference result evidence

## Coverage mapping

Execution results map into Sprint 17 coverage dispositions as follows:

| Adapter result | Coverage disposition |
| --- | --- |
| `pass` | `tested` |
| `fail` | `tested` |
| `warning` | `tested` |
| `skip` | `skipped` |
| `not_applicable` | `skipped` with not-applicable reason |

The adapter result keeps OSMAP-style precision while preserving the Sprint 17 coverage ledger model.

## Validation

Focused validation:

```bash
python -m pytest -q tests/test_wstg_execution_adapter.py
```

Full validation:

```bash
python -m compileall -q src tests
python -m pytest
bash scripts/validate-repository-safety.sh
python scripts/audit-commercial-release-readiness.py
```
