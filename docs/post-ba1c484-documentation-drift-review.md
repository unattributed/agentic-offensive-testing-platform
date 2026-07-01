# Post-ba1c484 Documentation Drift Review

Review date: 2026-07-01

Baseline commit: `ba1c484dc6a5cbc967a229059003c1472dde9499`

## Scope

This review checks the public documentation after Sprint 17 and the Sprint 17 follow-up merge. The focus is roadmap consistency, development-plan continuity, WSTG coverage language, WSTG execution-adapter language, live-adapter readiness, and public release safety posture.

## Findings

No documentation blockers were found. The repository direction remains local-first, authorized-only, evidence-first, FOSS-first, campaign-governed, public source-available, and fail-closed for commercial release.

The following drift items were corrected in this documentation alignment slice:

- `docs/development-plan.md` did not list the Sprint 17 follow-up hardening slice or its development evidence.
- `docs/development-plan.md` did not list `tests/test_wstg_error_input_browser.py` in Sprint 17 evidence.
- Sprint 18 did not explicitly consume the Sprint 17 follow-up execution adapter contract.
- `docs/sprint-17-wstg-campaign-coverage.md` did not cross-reference the merged follow-up contract for optional evidence-bound finding candidates.
- `docs/live-adapter-readiness.md` still described Sprint 15 as future work and did not mention Sprint 16, Sprint 17, or the Sprint 17 follow-up.
- `docs/wstg-mapping.md` did not explain the separation between WSTG coverage dispositions and OSMAP-style adapter result statuses.
- `README.md` did not describe the post-`ba1c484` WSTG coverage plus execution-adapter state.
- `CHANGELOG.md` did not summarize Sprints 15, 16, 17, or the Sprint 17 follow-up.

## Verified non-drift

- OSMAP and browser-suite remain external-reference-only sources. No OSMAP or browser-suite code is vendored.
- The Sprint 17 follow-up execution adapter remains network-silent by itself.
- Generated WSTG objectives still do not grant execution authority.
- Finding candidates remain evidence-bound and require failed, redacted execution results.
- Public repository visibility does not authorize operational use.
- Commercial, evaluator, operational material, and open-source release decisions remain blocked or prohibited according to the public release risk posture.

## Alignment rule going forward

Any sprint that changes the WSTG execution model must update all of the following in the same PR:

- `docs/development-plan.md`
- sprint-specific documentation under `docs/sprint-*`
- `docs/wstg-mapping.md` when mapping or status semantics change
- `docs/live-adapter-readiness.md` when execution or adapter posture changes
- `README.md` when user-facing operating mode changes
- `CHANGELOG.md`
