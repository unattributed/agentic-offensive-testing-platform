# Sprint 18 follow-up: local Juice Shop agentic campaign runner

## Purpose

This follow-up turns the Sprint 18 WSTG catalog, planning engine, and local Juice Shop benchmark into a first executable campaign path. It does not claim full vulnerability discovery. It proves AOTP can reset a known local benchmark, create a governed WSTG plan, make state-driven testing decisions, collect normalized evidence, create evidence-bound candidate findings, and compare observed WSTG coverage against the Juice Shop benchmark manifest.

## Scope

In scope:

- Loopback-only target `http://127.0.0.1:3000/`.
- Fresh local Juice Shop reset before campaign execution.
- Repository `.venv/bin/python` for AOTP code execution.
- Passive and safe-active GET-only checks.
- Same-origin requests to an allow-listed set of local benchmark paths.
- Evidence files, SHA256 hashes, benchmark comparison, and markdown report.

Out of scope:

- Public internet exposure.
- Challenge solutions.
- Destructive payloads.
- Credential guessing.
- State-changing POST, PUT, PATCH, or DELETE requests.
- Claims that every Juice Shop vulnerability has been found.

## Acceptance

This follow-up is accepted when:

1. The runner refuses non-loopback targets.
2. The runner uses the repository `.venv/bin/python` for all AOTP code.
3. The runner resets local Juice Shop before live campaign execution unless explicitly told not to.
4. The campaign builds a canonical WSTG plan before any request.
5. The campaign sends only bounded same-origin GET requests.
6. The campaign writes normalized evidence and SHA256 hashes.
7. The campaign produces candidate or manual-required findings only from collected evidence.
8. The benchmark comparison records detected and missed WSTG coverage.
9. Focused tests and the full project suite pass.

## Evidence outputs

A live run writes:

```text
inventory.txt
pre-campaign-root.html
reset/
campaign/campaign-plan.json
campaign/agent-decisions.jsonl
campaign/observations/http-observations.json
campaign/surface/discovered-surface.json
campaign/findings/candidate-findings.json
campaign/reports/benchmark-comparison.json
campaign/reports/campaign-report.md
campaign/campaign-result.json
campaign/SHA256SUMS
SHA256SUMS
```

## Command

```sh
scripts/run-local-juice-shop-agentic-campaign.sh \
  --repo "$HOME/Workspace/agentic-offensive-testing-platform" \
  --evidence-dir "$HOME/Downloads/aotp-local-juice-shop-agentic-campaign-$(date -u +%Y%m%d-%H%M%SZ)"
```

## Development note

This follow-up deliberately starts with safe, evidence-producing behavior. Later work should add browser-backed route discovery, authenticated account workflows, passive proxy capture, safe-active API checks, and human-reviewed exploit validation. Those later adapters must continue to report unsupported, denied, deferred, and manual-required coverage instead of inventing findings.
