# Live adapter readiness

Sprint 10 defines contracts only. It does not implement or enable network-capable adapters. This
is the current v0.1 state, not a permanent product restriction. Sprint 14 onward progressively
implements real campaign-governed native tools under the acceptance criteria in the development
plan.

| Adapter | Default mode | Modeled capability | Live execution |
|---|---|---|---|
| Playwright | `dry_run` | navigation, DOM, screenshot, and trace placeholders | Disabled |
| ZAP | `dry_run` | passive scan and limited spider placeholders | Disabled |
| mitmproxy | `dry_run` | authorized local capture placeholders | Disabled |
| OSMAP | `external_reference_only` | case aliases and external evidence references | Disabled |
| WSTG execution adapter | `contract_only` | governed execution request, result, evidence, coverage, and finding-candidate contracts | Disabled by itself |
| browser-suite | `external_reference_only` | artifact classes and external evidence references | Disabled |

Every contract requires explicit private scope and policy approval. Network-capable contracts also
declare rate or spider boundaries, evidence rules, future readiness review, and adapter-specific
approval. Every contract defaults to network silent, a zero request budget, and
`live_execution_enabled: false`.

The registry does not grant authority. Each implementation must add private runtime
configuration, deterministic policy integration, dependency and license review, bounded execution,
redaction, evidence integrity, negative tests, and explicit operator review before changing any
live-execution flag.

Post-`ba1c484`, the accepted post-Sprint 13 tool path includes Sprint 14 Deep Agent metadata
execution, Sprint 15 campaign-governed native tool enforcement, Sprint 16 sensitive evidence vault
handling, Sprint 17 WSTG objective and coverage planning, and the Sprint 17 follow-up WSTG
execution adapter contract. The adapter contract defines governed execution requests, OSMAP-style
results, redacted evidence references, coverage updates, and evidence-bound finding candidates, but
it is network-silent by itself and does not invoke a process. MCP is not part of this core path.

OSMAP and browser-suite remain separate projects. Their bridges validate metadata references only.
They do not import source code, invoke a process, or commit generated evidence. The Sprint 17
follow-up makes the OSMAP-style result discipline reusable without vendoring or executing OSMAP.
Browser-suite references additionally require a separate license review record because the source
project declares `AGPL-3.0-or-later`.

The examples in `examples/adapters/deferred-adapters.placeholder.yaml` contain aliases only. The
parser rejects target URLs, enabled execution, nonzero request budgets, missing requirements,
unsupported capabilities, unsafe aliases, and duplicate declarations.
