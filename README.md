# Agentic Offensive Testing Platform

Agentic Offensive Testing Platform (AOTP) is a public source-available, policy-constrained framework for bounded, evidence-first offensive security campaigns against explicitly authorized assets. It is designed for candidate evaluations, evaluator reviews, client-authorized demonstrations, and bug bounty style assessments.

> **Authorized use only.** Scope is authoritative. Safe harbor, an MNDA or confidentiality agreement, evaluator consent, public repository visibility, or general authorization never expands technical scope beyond the assets, accounts, services, APIs, windows, and categories in the private scope file.

## Operating model

**Public code, private operations, safe-by-default, live-by-authorization, license-aware.**

AOTP is a policy-constrained campaign harness. AI may propose objectives, summarize redacted evidence, classify likely risk, and draft evidence-bound language. AI cannot authorize scope, add targets, override rules of engagement, bypass the policy gate, continue after a stop condition, or submit a report.

AOTP is not an uncontrolled autonomous pentest bot, program enrollment tool, target scraper, high-volume scanner, automatic report submitter, or guarantee of bug bounty income. The initial live adapters are intentionally network-silent stubs.

## Campaign loop

```text
private program profile + private technical scope
                       |
                       v
approved campaign -> deterministic scheduler -> policy gate
                                               | deny
                                               v
                                      stopped-by-policy evidence
                                               |
                                      allow    v
planner suggestion -> approved objective -> adapter contract
                                               |
                                               v
                                      evidence + hashes
                                               |
                                               v
                                  verifier -> candidate lifecycle
                                               |
                                               v
                                human gate -> evidence-only report
```

Each iteration reads the scope and rules of engagement, selects an already approved objective, evaluates it at the policy gate, invokes a deterministic adapter, captures evidence, records state, updates candidate references, and decides whether to continue, pause, or stop. The scheduler selects the lowest-priority-number pending objective. AI suggestions are accepted only when they match an approved objective identifier.

Campaign state is JSON under the ignored `.aotp/state/` directory. It records the scope hash, authorization and rules-of-engagement references, timestamps, module dispositions, finding candidate references, evidence directories, counters, events, and stop history.

[LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence) is implemented as the durable orchestration option for checkpointed state and human interrupts. It advances the same deterministic reference engine one objective at a time, so graph execution cannot bypass policy, evidence, budgets, or the event chain. The boundary is documented in [docs/langgraph-orchestration.md](docs/langgraph-orchestration.md).

## Safety boundaries

A fresh clone, CI, tests, example files, `make dry-run`, and all quick-start commands send no traffic to third-party targets. Live mode requires a private untracked program profile and scope, non-placeholder written authorization and agreement references, confirmed rules of engagement, confidentiality confirmation when applicable, an allowed window, explicit targets and categories, rate limits, evidence rules, disclosure rules, stop conditions, and `--operator-approved`.

The policy gate denies missing or malformed scope, target or service expansion, forbidden actions, unapproved fuzzing, unapproved control-panel or cryptographic review, unprovided SBOM artifacts, absent human approval, unsafe evidence paths, and failed redaction. Even after a live request passes these checks, version 0.1 returns `manual_review` from a network-silent adapter stub.

Public repository visibility does not make operational use public. Real targets, organization names, profiles, accounts, correspondence, findings, screenshots, reports, traces, generated captures, and evidence must never be committed.

## Quick start

Python 3.11 or newer is required.

```bash
./scripts/bootstrap.sh
. .venv/bin/activate
make check
aotp validate-config --scope config/scope.example.yaml
aotp list-cases
aotp list-modules
aotp dry-run --scope config/scope.example.yaml
aotp campaign-plan \
  --scope config/scope.example.yaml \
  --campaign campaigns/authorized-webapp-campaign.example.yaml
```

Before any live case, run the non-executing `aotp policy-check` with the private scope, program profile, approval record, case, `--live`, and `--operator-approved`. It returns a structured allow or deny decision and creates no evidence or network traffic.

Run a safe case:

```bash
aotp run-case \
  --scope config/scope.example.yaml \
  --case cases/wstg-security-headers.example.yaml \
  --dry-run
```

Run a network-silent campaign and create ignored local state and evidence:

```bash
aotp campaign-run \
  --scope config/scope.example.yaml \
  --campaign campaigns/authorized-webapp-campaign.example.yaml
```

Run the service control panel campaign with its mandatory lockout-risk stop condition:

```bash
aotp campaign-run \
  --scope config/scope.panel-dry-run.example.yaml \
  --campaign campaigns/service-control-panel-campaign.example.yaml
```

Run the same deterministic engine under durable LangGraph orchestration:

```bash
aotp campaign-graph-run \
  --scope config/scope.example.yaml \
  --campaign campaigns/authorized-webapp-campaign.example.yaml
```

The graph stores only aliases, hashes, status, and local state references in a mode-`0600` SQLite checkpoint. Policy, evidence, budgets, and the event chain remain owned by the deterministic engine. A paused graph resumes only with `campaign-graph-resume` and a private checkpoint-bound review file.

## Live authorized flow

1. Accept and record the program or engagement policy in a private untracked program profile.
2. Create a separate private scope file with aliases, explicit technical boundaries, accounts, windows, categories, budgets, evidence rules, and stop conditions.
3. Confirm the authorization, agreement, confidentiality, and rules-of-engagement references.
4. Validate the profile and scope manually, then run `validate-config` and `campaign-plan`.
5. Obtain any objective-specific human approvals.
6. Invoke `campaign-run --live --operator-approved` with the private program profile and approval arguments.
7. Review the resulting `manual_review` state before adding or enabling a future live adapter.

The example scope is deliberately incapable of authorizing live work.

Live commands also require `--program-profile <private-profile.yaml>` and `--approval <private-approval.yaml>`. The approval record is bound to the exact scope file SHA256, authorization reference, operator alias, expiry, and approved objective or campaign identifiers. The boolean flag is an additional runtime confirmation, not a substitute for the record.

## Cases and modules

- **WSTG web application:** case YAML records an identifier, approved action, target alias, approval need, and version-aware WSTG mapping where applicable. Coverage includes authentication, sessions, authorization, input validation, headers, client-side behavior, and business logic.
- **Service control panels:** safe observations cover an explicitly listed panel, TLS, headers, login exposure, default pages, version leakage, indexing, and unauthenticated metadata. Credential attacks, lockout behavior, destructive administration, and target expansion are denied.
- **Bounded fuzzing:** authorization, payload and request budgets, per-endpoint limits, response limits, runtime, retries, safe payload classes, and stop conditions are mandatory. Payment, KYC, support, recovery, authentication abuse, destructive, and unapproved state-changing workflows are denied.
- **SBOM and configuration review:** only provided artifacts are eligible. Evidence separates component presence from verified reachability or exploitability.
- **Cryptographic controls:** review is limited to scoped TLS, certificate metadata, cookie attributes, provided token configuration, dependency exposure, algorithm indicators, and key-management configuration. Private-key extraction, brute force, and destructive testing are denied.

The methodology follows the [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/). Mapping details and versioning rules are in [docs/wstg-mapping.md](docs/wstg-mapping.md).

## Evidence, candidates, and reports

Every executed or denied objective produces an evidence manifest with campaign and iteration identity, aliases, authorization references, mappings, adapter, mode, policy decision, counters, artifact placeholders, hashes, verdict, confidence, candidate reference, inclusion status, and redaction status.

Only `pass`, `fail`, `inconclusive`, `manual_review`, and `stopped_by_policy` are valid verifier verdicts. Severity candidate, confidence, evidence strength, and human validation are independent. An observation moves through an explicit lifecycle before it can become `ready_for_report`. Reports render recorded fields only and never invent vulnerabilities, affected assets, exploitation paths, impact, or remediation.

The usable evidence pipeline is:

```text
evidence.json -> evidence-verdict -> finding-create
              -> finding-transition -> report
```

Each stage verifies the integrity and provenance of the previous stage. Only a human-validated `ready_for_report` candidate can appear as a finding in the generated draft.

Service control panel evidence adds a manifest-bound review decision before candidate creation:

```text
evidence.json -> report-review-create -> finding-create --report-review <decision>
```

The reporter independently re-derives this requirement from the evidence manifest and renders only
validated fields from the hashed `panel-evidence.json` artifact.

Bug bounty drafts remain drafts until a human approves them. AOTP has no submission adapter.

## Local models

The Ollama adapter defaults to `http://localhost:11434`, requests structured JSON, and sanitizes prompts before sending them. Model examples include `qwen3:8b`, `qwen2.5-coder:7b`, `qwen2.5-coder:14b`, `deepseek-r1:8b`, and `qwen3-vl:8b`. Credentials, cookies, bearer tokens, session identifiers, private keys, and email addresses are blocked or redacted. See the [Ollama structured outputs documentation](https://docs.ollama.com/capabilities/structured-outputs).

## Integration boundaries

Playwright, ZAP, and mitmproxy are optional future adapters with declared supported, required, and denied actions. Their designs reference the official [Playwright tracing](https://playwright.dev/docs/trace-viewer), [ZAP Automation Framework](https://www.zaproxy.org/docs/automate/automation-framework/), and [mitmproxy](https://docs.mitmproxy.org/stable/) documentation.

OSMAP and `ai-browser-security-test-suite` are optional local integration points, not dependencies. AOTP uses clean-room contracts and external evidence references instead of vendored code. This preserves repository and licensing boundaries, including the browser suite's separate license obligations.

## Evaluation positioning

AOTP demonstrates evidence-first, WSTG-aligned, policy-constrained testing; safe handling of provisioned accounts; reproducible evidence; scoped SBOM and configuration review; bounded fuzzing; cryptographic and control-panel review; no unauthorized expansion; no credential leakage; no uncontrolled scanning; and reporting based only on captured evidence.

It can be adapted to a candidate lab, evaluator-provisioned service, client engagement, or accepted bug bounty program by replacing placeholders with private aliases and written scope. Real targets, organization names, profiles, accounts, correspondence, findings, screenshots, and evidence must never be committed.

## Repository and licensing status

This repository is public source-available work with all rights reserved. No open-source license is granted. See [LICENSE.md](LICENSE.md), [repository redaction policy](docs/repository-redaction-policy.md), [licensing readiness](docs/licensing-readiness.md), [commercialization plan](docs/commercialization-plan.md), and [public release risk review](docs/public-release-risk-review.md).

Third-party dependencies are minimal and tracked for later legal review. Generated evidence, profiles, candidate data, and campaign memory stay untracked.

Development agents follow the [engineering agent SOP](docs/engineering-agent-sop.md) and the slice-based [development plan](docs/development-plan.md).

External YAML and YARA sources are disabled unless a private registry pins their repository commit, local bundle hash, license review, template identifiers, capabilities, and mandatory denials. See the [template ecosystem evaluation](docs/template-ecosystem-evaluation.md).
