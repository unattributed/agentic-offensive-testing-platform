# Development plan

This plan directs AOTP toward professional, evidence-first, authorized offensive web application testing. The project goal is not to collect vulnerable lab targets. The goal is to build agentic workflows that plan, execute, observe, validate, refine, and report web application security testing with the diligence expected from a senior web application penetration testing team.

The [engineering agent SOP](engineering-agent-sop.md) governs branch, test, commit, and synchronization behavior.

For every slice below, validation includes the listed focused command plus `python3 -m compileall src tests`, `python3 -m pytest`, `./scripts/validate-repository-safety.sh`, and `make test` when those commands are available in the checkout. Evidence includes command output, focused test names, reviewed diff, target-state proof when a live target is used, and a no-private-material confirmation. Files are the named areas plus adjacent tests and documentation. Every suggested commit message is lowercase.

## Direction of travel

AOTP must become a platform that can complete authorized testing campaigns through agentic loops:

```text
authorized scope -> WSTG plan -> agent tasking -> governed execution -> evidence -> proof request -> validation -> finding lifecycle -> professional report
```

The project must produce real testing outcomes:

- real tests, not only planning artifacts
- real evidence, not unsupported assertions
- real candidate findings, bound to artifacts
- vetted and validated findings, not scanner noise or agent guesses
- false-positive rejection, duplicate handling, and out-of-scope stops
- reproducible proof steps and professional report packages
- campaign summaries that explain tested, skipped, denied, deferred, and blocked work

HackerOne or Bugcrowd compatibility is an output mode, not the only destination. The same validated findings must also support internal AppSec review, external client assessment, candidate evaluation, executive review, and developer remediation.

## Target strategy

No more local vulnerable targets are planned during the next execution-depth phase. Juice Shop is the active local live benchmark. crAPI remains registered as a planned benchmark profile with live runtime pending. Future external testing must use authorized program scope, such as HackerOne campaigns, only after the local benchmark workflow can demonstrate real agentic testing depth.

Target policy:

- Juice Shop is the resettable loopback-only live benchmark for execution-depth work.
- crAPI is a registered planned benchmark target with WSTG mapping, but live runtime is pending and not accepted.
- AOTP must not make any target a dependency of the WSTG engine.
- New target additions are deferred until the generic workflow, validation, and reporting layers are proven.

## Professional finding standard

A finding can become reportable only after it passes a lifecycle gate. AOTP must not report observations, guesses, or raw scanner output as validated vulnerabilities.

Finding lifecycle:

```text
observed -> candidate -> needs_more_evidence -> needs_human_approval -> validated -> report_ready
observed -> candidate -> rejected_false_positive
observed -> candidate -> duplicate
observed -> candidate -> out_of_scope
```

Report-ready findings require:

- title
- affected asset or endpoint
- scope decision and ROE reference
- WSTG category
- CWE or OWASP mapping when supported
- severity recommendation and confidence
- evidence files and hashes
- reproduction steps
- validation steps performed
- false-positive checks performed
- impact statement supported by evidence
- limitations and what was not tested
- remediation guidance
- safe retest steps

## Agentic workflow model

AOTP must support assigned agents with auditable responsibilities. Agents do not merely produce text. Agents create or update campaign state, request actions, execute governed tools, record evidence, and explain decisions.

| Agent | Responsibility | Required outputs |
|---|---|---|
| Campaign Lead Agent | Maintains campaign goals, WSTG coverage, budgets, and stop conditions | campaign state, next objective rationale, stop or continue decision |
| Browser Workflow Agent | Uses governed Playwright to navigate, observe pages, capture DOM, screenshots, links, forms, and session state | browser evidence, route observations, session state references |
| Authentication Agent | Handles provisioned accounts, login state, logout proof, and session classification | vaulted credential references, auth state evidence, boundary checks |
| Form Action Agent | Discovers forms, classifies risk, proposes safe submissions, and requests approval for risky actions | form inventory, action proposals, submission evidence |
| API Discovery Agent | Extracts API routes from browser traffic, OpenAPI, GraphQL, JavaScript references, and observed requests | API inventory, provenance, scope decisions |
| Evidence Auditor Agent | Determines whether evidence is sufficient, stale, contradictory, or missing | proof requests, sufficiency verdicts |
| Validation Agent | Performs ROE-gated confirmation of candidate findings | validation action records, confidence updates |
| Reporting Agent | Converts validated findings into professional packages for the selected audience | finding package, campaign report, evidence appendix |

## ROE gates

Every execution path must remain authorized and controlled. AOTP must fail closed when authority, scope, budget, or evidence handling is unclear.

Required gates:

- passive-only mode
- safe active mode
- authenticated testing mode
- form submission approval
- state-changing action approval
- proof action approval
- destructive action prohibition
- rate limit and request budget enforcement
- out-of-scope stop
- credential and session handling policy
- sensitive data classification and vault handling
- manual-only external disclosure

## Completed foundation through Sprint 18H

The following completed work remains part of the project baseline. Historical detail is preserved in sprint-specific documents and commit history. Future work must build on these foundations rather than bypass them.

| Sprint | Completed capability | Current acceptance boundary |
|---|---|---|
| 0 | Private-safe repository foundation, metadata, CI baseline, policy scaffold | repository safety and tests pass |
| 1 | Scope, authorization, and rules of engagement | live work requires explicit authority and operator approval |
| 2 | Campaign loop and campaign state foundations | bounded state, stop behavior, and checkpoint concepts exist |
| 3 | Evidence and candidate pipeline | evidence hashes, redaction, and evidence-bound candidates are foundational |
| 4 | WSTG web application module contracts | WSTG cases and adapter contracts are safe and initially network-silent |
| 5 | Service control panel misconfiguration workflow | scoped management-interface checks are evidence-bound and gated |
| 6 | Bounded fuzzing policy | fuzzing requires explicit authorization, budgets, and instability stops |
| 7 | SBOM and dependency review | provided artifacts are hashed and presence is separated from exploitability |
| 8 | Cryptographic controls review | scoped observable crypto evidence is handled safely |
| 9 | HTTP security and browser-control review | browser-facing controls are modeled safely |
| 10 | Access control and session review foundations | auth and session checks remain governed |
| 11 | Input and error-boundary review foundations | input evidence and error behavior are bounded |
| 12 | Campaign report and evidence packaging foundations | report generation remains evidence-bound |
| 13 | Post-sprint alignment and documentation cleanup | stale blockers and target-specific drift are reduced |
| 14 | Deep agent runtime foundations | local agent runtime work is available for later orchestration |
| 15 | Campaign-governed native tool registry | governed tools mediate execution and budget |
| 15A | Tool registry hardening | target expansion and out-of-origin evidence are blocked |
| 16 | Sensitive evidence vault and PoC material handling | sensitive material is classified, vaulted, and export-gated |
| 17 | WSTG campaign coverage engine | WSTG objectives derive from scope, ROE, and evidence gaps |
| 17F | WSTG execution adapter contract | generated objectives can map to governed execution requests and evidence-backed results |
| 18 | Authenticated OSMAP and clearbox workflow | retained as a narrow integration example, not an engine dependency |
| 18F | Local Juice Shop benchmark | Juice Shop is loopback-only, resettable, and separate from the engine |
| 18G | Local Juice Shop agentic campaign runner | first bounded local live campaign exists, but is still limited and GET-oriented |
| 18H | Local vulnerable target matrix | Juice Shop is implemented; OWASP crAPI is a planned registered target with live runtime pending, without making crAPI a dependency of the WSTG engine |

Sprint 18H correction: crAPI live runtime is not accepted on the Parrot rootless Podman Compose host. The plan must not claim that crAPI live reset, health verification, or `127.0.0.1:8888` runtime support is complete. The accepted value from Sprint 18H is the target matrix registry, crAPI metadata profile, and crAPI WSTG mapping.

## Sprint 18F: Local Juice Shop WSTG Campaign Benchmark

Goal: preserve the accepted loopback-only OWASP Juice Shop benchmark work as the active local live proving ground for execution-depth development. Juice Shop is a resettable benchmark resource, not an engine dependency, and must remain separate from WSTG planning logic.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 18F.1 benchmark inventory | Inventory the local Parrot system and required tools before using the target | Evidence records user, OS, container runtime, curl, Python, git, and listener state | `pytest tests/test_juice_shop_local_scripts.py` | inventory output | `scripts/install-local-juice-shop-benchmark.sh`, tests | `inventory local juice shop benchmark` |
| 18F.2 loopback reset | Reset Juice Shop before every live campaign | Old container is removed and a fresh loopback-only container starts without persistent mounts | `scripts/juice-shop-local-reset.sh --help` | reset evidence | `scripts/juice-shop-local-reset.sh` | `reset local juice shop benchmark` |
| 18F.3 benchmark profile | Keep a metadata-only Juice Shop lab target profile | Profile cannot become a WSTG engine dependency or challenge-solution shortcut | `pytest tests/test_juice_shop_local_profile.py` | profile fixture | `src/aotp/lab_targets/juice_shop.py` | `add juice shop local profile` |
| 18F.4 benchmark mapping | Map broad Juice Shop vulnerability classes to canonical WSTG IDs | Mapping contains no copied solutions and no challenge-specific bypasses | `pytest tests/test_juice_shop_benchmark_mapping.py` | benchmark fixture | `src/aotp/benchmarks/juice_shop.py` | `map juice shop benchmark coverage` |
| 18F.5 local validation runner | Preserve the venv-backed validation runner for the benchmark | Runner can validate project tests and optionally reset the live local benchmark | `pytest tests/test_development_plan_juice_shop_followup.py` | runner output | `scripts/run-sprint18-followup-local-juice-shop-validation.sh` | `validate local juice shop benchmark` |

Development evidence: `src/aotp/lab_targets/juice_shop.py`, `src/aotp/benchmarks/juice_shop.py`, `scripts/install-local-juice-shop-benchmark.sh`, `scripts/juice-shop-local-reset.sh`, `scripts/run-sprint18-followup-local-juice-shop-validation.sh`, `docs/lab-targets/juice-shop-local.md`, `docs/sprint-18-followup-local-juice-shop-benchmark.md`, `tests/test_juice_shop_local_profile.py`, `tests/test_juice_shop_benchmark_mapping.py`, `tests/test_juice_shop_local_scripts.py`, and `tests/test_development_plan_juice_shop_followup.py`.

Sprint acceptance: the loopback-only OWASP Juice Shop benchmark remains resettable, local, and separate from the WSTG engine. The plan keeps local Juice Shop benchmark fixtures available for execution-depth work while preventing benchmark-specific shortcuts.

## Sprint 18G: Local Juice Shop Agentic Campaign Runner

Goal: preserve the accepted first executable AOTP-owned campaign path against the loopback-only Juice Shop benchmark. This runner is useful as a baseline, but it is not the final agentic testing model. Future sprints must generalize it into reusable WSTG execution, stateful browser workflows, proof requests, validation loops, and professional reporting.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 18G.1 campaign runner | Preserve the local Juice Shop campaign module that validates loopback scope, builds a WSTG plan, performs bounded same-origin GET requests, and records state-driven decisions | Non-loopback targets and unsafe paths are rejected; requests remain bounded | `pytest tests/test_juice_shop_agentic_campaign.py` | campaign result fixture | `src/aotp/campaigns/juice_shop_campaign.py` | `preserve juice shop campaign runner` |
| 18G.2 evidence output | Preserve campaign plan, decisions, HTTP observations, surface inventory, candidate findings, benchmark comparison, report, and hashes | Evidence paths are deterministic and report content is evidence-bound | `pytest tests/test_juice_shop_agentic_campaign.py -k writes_evidence` | generated evidence tree | campaign module and docs | `record juice shop campaign evidence` |
| 18G.3 live runner script | Preserve the venv-backed live runner that resets local Juice Shop before campaign execution | Reset is default, `--no-reset` is explicit, and evidence is captured | `pytest tests/test_juice_shop_agentic_campaign_scripts.py` | runner output | `scripts/run-local-juice-shop-agentic-campaign.sh` | `run juice shop agentic campaign` |
| 18G.4 generalization boundary | Document that the runner is a baseline for generic execution, not a target-specific model to copy | Later sprints must remove target-specific shortcuts from the main execution harness | development plan guard tests | roadmap evidence | docs and campaign modules | `document juice shop runner boundary` |

Development evidence: `src/aotp/campaigns/juice_shop_campaign.py`, `scripts/run-local-juice-shop-agentic-campaign.sh`, `docs/sprint-18-followup-local-juice-shop-agentic-campaign.md`, `tests/test_juice_shop_agentic_campaign.py`, and `tests/test_juice_shop_agentic_campaign_scripts.py`.

Sprint acceptance: AOTP can run a bounded local Juice Shop campaign that resets the target, plans WSTG work, executes safe local requests, writes evidence, creates evidence-bound candidate findings, and reports benchmark coverage without embedding Juice Shop challenge solutions. The accepted limitation is explicit: this is an early bounded campaign runner, not a complete autonomous penetration tester.

## Sprint 18H: Local Vulnerable Target Matrix

Goal: preserve the accepted Sprint 18H boundary while preventing future drift back into target collection. AOTP includes a local target matrix registry. Juice Shop is the implemented resettable live benchmark. OWASP crAPI is the first additional planned target in the registry, with live runtime pending because the Parrot rootless Podman Compose path did not produce deterministic clean startup. The crAPI profile and WSTG mapping remain useful planning assets without making crAPI a dependency of the WSTG engine.

Sprint 18H acceptance boundary: the accepted implementation is the local target matrix registry, Juice Shop implemented live target metadata, crAPI planned target metadata, and crAPI WSTG benchmark mapping. crAPI live runtime, reset, health verification, and `127.0.0.1:8888` acceptance are not complete and must not be treated as available until a later dedicated runtime-hardening sprint proves deterministic startup, health, cleanup, and evidence capture.

## Sprint 19: Generic Agentic WSTG Execution Harness

Goal: replace target-specific campaign logic with a generic WSTG live execution harness that can run approved objectives against an approved target profile through governed tools, record evidence, update campaign state, and emit candidate findings without target-specific shortcuts.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 19.1 campaign target contract | Define a generic target runtime contract for loopback, bug bounty, and internal AppSec profiles | Juice Shop uses the contract; crAPI remains planned and not executable | `pytest tests/test_target_runtime_contract.py` | target runtime fixture | `src/aotp/campaigns/target_runtime.py`, tests | `add generic target runtime contract` |
| 19.2 WSTG live campaign model | Define campaign input, objective queue, action queue, state, budget, and evidence references | Campaign state round trips and denies missing scope | `pytest tests/test_wstg_live_campaign.py` | state fixture | `src/aotp/campaigns/wstg_live_campaign.py`, `src/aotp/campaigns/campaign_state.py` | `add generic wstg live campaign model` |
| 19.3 execution planner | Select the next executable WSTG objective from coverage gaps, ROE, and available tools | Selection explains why objectives are executed, deferred, denied, or blocked | `pytest tests/test_execution_planner.py` | decision log | `src/aotp/campaigns/execution_planner.py` | `add evidence driven execution planner` |
| 19.4 governed tool invocation | Route every action through the governed tool registry with request budget reservation | No direct network or browser action bypasses the registry | `pytest tests/test_wstg_tool_invocation.py` | registry-mediated action record | campaign and tool registry modules | `route wstg actions through governed tools` |
| 19.5 generic evidence writer | Write normalized campaign plan, decisions, observations, coverage, candidates, and hashes | Evidence paths are deterministic and redacted | `pytest tests/test_campaign_evidence_writer.py` | evidence tree fixture | `src/aotp/campaigns/evidence_writer.py` | `write generic campaign evidence` |
| 19.6 Juice Shop adapter migration | Migrate the existing Juice Shop runner onto the generic harness | Live Juice Shop campaign still passes and contains no challenge-solution shortcuts | `pytest tests/test_juice_shop_agentic_campaign.py tests/test_wstg_live_campaign.py` | local campaign archive | Juice Shop campaign and target modules | `migrate juice shop to generic wstg harness` |
| 19.7 proof request output | Generate proof requests when evidence is insufficient instead of overclaiming | Candidate remains unvalidated until proof exists | `pytest tests/test_proof_requests.py` | proof request JSON | `src/aotp/campaigns/proof_requests.py` | `add campaign proof requests` |

Sprint acceptance: AOTP can run a generic WSTG campaign against the supported local Juice Shop profile, maintain campaign state, choose next WSTG objectives from evidence gaps, execute only through governed tools, write normalized evidence, generate proof requests, and produce evidence-bound candidate findings. crAPI remains registered but not live-executable.

## Sprint 20: Stateful Browser Workflows and Authenticated Sessions

Goal: add a Playwright-backed, governed browser workflow engine that can navigate, observe, authenticate with provisioned accounts, preserve classified session state, and feed route, DOM, link, screenshot, and form observations back into the WSTG campaign loop.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 20.1 Playwright governed adapter | Implement Playwright through the governed tool registry with same-origin and budget enforcement | Browser actions deny out-of-scope URLs and direct execution bypass | `pytest tests/test_playwright_browser_governed.py` | action and denial records | `src/aotp/agent_tools/playwright_browser.py`, tests | `add governed playwright browser adapter` |
| 20.2 browser observation model | Capture DOM metadata, visible text summaries, screenshots, links, frames, cookies metadata, and storage metadata | Sensitive values are classified or redacted | `pytest tests/test_browser_observation.py` | observation fixture | `src/aotp/browser_observation.py` | `record browser workflow observations` |
| 20.3 session state handling | Store provisioned account session state through vault or memory-only policy | Cookies and tokens never enter public evidence | `pytest tests/test_authenticated_session_state.py` | session evidence | `src/aotp/authenticated_session.py`, vault modules | `handle authenticated browser sessions` |
| 20.4 login workflow runner | Support provisioned login steps without credential guessing | Login requires provided credentials and ROE authorization | `pytest tests/test_login_workflow.py` | auth workflow artifact | `src/aotp/workflows/login.py` | `add provisioned login workflow` |
| 20.5 logout and boundary proof | Verify logout, post-logout access, and session invalidation when approved | Boundaries are recorded without exposing secrets | `pytest tests/test_logout_boundary.py` | boundary evidence | `src/aotp/workflows/logout_boundary.py` | `verify authenticated session boundaries` |
| 20.6 browser-to-WSTG mapper | Map browser observations to WSTG objectives and evidence gaps | Routes, forms, and session observations update coverage | `pytest tests/test_browser_wstg_mapper.py` | coverage update fixture | `src/aotp/wstg/browser_mapper.py` | `map browser observations to wstg coverage` |

Sprint acceptance: AOTP can use governed Playwright to perform stateful browser observation, provisioned login, classified session handling, logout proof, and WSTG coverage updates without credential guessing or out-of-scope browsing.

## Sprint 21: Form Discovery, API Discovery, and Controlled Action Chains

Goal: let the agent discover forms, classify actions, observe APIs, build controlled multi-step action chains, and request human approval before any risky or state-changing action.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 21.1 form discovery | Inventory forms, methods, fields, CSRF indicators, and visible context | Raw secret values and entered credentials are not persisted | `pytest tests/test_form_discovery.py` | form inventory fixture | `src/aotp/form_discovery.py` | `discover browser forms safely` |
| 21.2 form risk classifier | Classify forms as passive, safe submit, state-changing, auth, destructive, or approval-required | Destructive or unclear forms deny by default | `pytest tests/test_form_risk_classifier.py` | classification matrix | `src/aotp/form_risk.py` | `classify form action risk` |
| 21.3 controlled submission planner | Generate safe submissions only when ROE, budget, and field policy permit | Submission plans require evidence and approval when needed | `pytest tests/test_controlled_submission.py` | planned action records | `src/aotp/controlled_submission.py` | `plan controlled form submissions` |
| 21.4 browser traffic observer | Capture request and response metadata from browser activity | Request bodies and sensitive headers are classified or redacted | `pytest tests/test_browser_traffic_observer.py` | traffic observation fixture | `src/aotp/agent_tools/http_observer.py` | `observe browser api traffic` |
| 21.5 API route discovery | Discover API routes from observed traffic, OpenAPI, GraphQL introspection when approved, and JavaScript references | Routes keep provenance and scope decision | `pytest tests/test_api_route_discovery.py` | API inventory | `src/aotp/api_route_discovery.py` | `discover scoped api routes` |
| 21.6 action chain model | Define ordered, replayable, policy-checked action chains | Chains cannot skip approval or exceed budget | `pytest tests/test_action_chains.py` | action chain fixture | `src/aotp/action_chains.py` | `add controlled action chains` |
| 21.7 human approval interrupts | Pause for approval with exact context when proof or mutation risk requires it | Resume rechecks policy and approval identity | `pytest tests/test_human_approval_interrupts.py` | approval transcript | approval and campaign modules | `gate risky action chains` |

Sprint acceptance: AOTP can discover forms and API routes, classify risk, plan controlled submissions, build multi-step action chains, and pause for exact human approval before risky proof actions.

## Sprint 22: Evidence-Driven Proof Requests and Finding Validation

Goal: move from candidate observations to validated findings by requiring missing-proof requests, sufficiency checks, controlled validation actions, confidence updates, false-positive rejection, duplicate handling, and explicit lifecycle transitions.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 22.1 finding lifecycle state machine | Implement observed, candidate, needs_more_evidence, needs_human_approval, validated, rejected_false_positive, duplicate, out_of_scope, and report_ready states | Invalid transitions fail | `pytest tests/test_finding_lifecycle.py` | lifecycle matrix | `src/aotp/finding_lifecycle.py` | `add validated finding lifecycle` |
| 22.2 evidence sufficiency rules | Define minimum evidence per finding type and WSTG category | Candidate cannot validate without required proof | `pytest tests/test_evidence_sufficiency.py` | sufficiency cases | `src/aotp/evidence_sufficiency.py` | `require finding evidence sufficiency` |
| 22.3 proof request generator | Produce specific proof requests for missing exploitability, impact, reproduction, or scope evidence | Requests cite exact missing fields | `pytest tests/test_proof_request_generator.py` | proof request artifacts | `src/aotp/proof_request_generator.py` | `generate missing proof requests` |
| 22.4 validation action planner | Convert proof requests into ROE-gated validation actions | Risky actions require approval; denied actions leave finding unvalidated | `pytest tests/test_validation_action_planner.py` | validation plan | `src/aotp/validation_action_planner.py` | `plan governed validation actions` |
| 22.5 false-positive rejection | Reject weak candidates with evidence-backed reasons | Rejection is auditable and cannot silently disappear | `pytest tests/test_false_positive_rejection.py` | rejection record | `src/aotp/false_positive_rejection.py` | `reject false positive candidates` |
| 22.6 duplicate and prior-art review | Identify duplicate, previously reported, and low-value issues when evidence supports it | Duplicate state preserves evidence and rationale | `pytest tests/test_duplicate_review.py` | duplicate review fixture | `src/aotp/duplicate_review.py` | `review duplicate finding candidates` |
| 22.7 confidence scoring | Compute confidence from evidence quality, reproducibility, validation, and limitations | Confidence cannot exceed evidence support | `pytest tests/test_finding_confidence.py` | confidence cases | `src/aotp/finding_confidence.py` | `score finding confidence from evidence` |
| 22.8 campaign validation dashboard | Emit JSON and Markdown summary of candidate status and outstanding proof requests | Dashboard matches lifecycle state | `pytest tests/test_validation_dashboard.py` | dashboard artifact | `src/aotp/validation_dashboard.py` | `summarize finding validation state` |

Sprint acceptance: AOTP cannot validate a finding without sufficient evidence, cannot hide rejected candidates, requests missing proof instead of overclaiming, and produces an auditable validation dashboard.

## Sprint 23: Reproducible PoC Steps and Safe Retest Workflows

Goal: build reproducible proof-of-concept and retest workflows that preserve sensitive material safely, separate public and restricted evidence, and generate exact steps for validated findings without uncontrolled exploitation.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 23.1 PoC workspace contract | Define public, restricted, secret, poc_sensitive, recipient_only, and do_not_store handling in PoC workspaces | Public reports never contain raw sensitive material | `pytest tests/test_poc_workspace_contract.py` | workspace fixture | `src/aotp/poc_workspace.py` | `define reproducible poc workspace` |
| 23.2 reproduction step builder | Generate step-by-step reproduction from validated action chains and evidence | Steps are ordered, scoped, and replayable | `pytest tests/test_reproduction_steps.py` | reproduction document | `src/aotp/reproduction_steps.py` | `build evidence linked reproduction steps` |
| 23.3 proof artifact minimization | Store only necessary proof artifacts and classify sensitive annex material | Unneeded sensitive material is not exported | `pytest tests/test_proof_artifact_minimization.py` | artifact manifest | PoC and evidence modules | `minimize proof artifacts` |
| 23.4 safe retest plan | Generate retest steps that avoid destructive or high-risk behavior unless authorized | Retest plan reuses ROE gates | `pytest tests/test_safe_retest_plan.py` | retest plan | `src/aotp/safe_retest.py` | `generate safe retest steps` |
| 23.5 remediation verification hooks | Link retest evidence back to original finding and fix claim | Verification cannot bypass current policy | `pytest tests/test_remediation_verification.py` | verification record | `src/aotp/remediation_verification.py` | `verify remediation evidence` |
| 23.6 replayable local proof | Replay approved local benchmark steps under current policy | Replay denies if scope or ROE changes | `pytest tests/test_poc_replay.py` | replay transcript | `src/aotp/poc_replay.py` | `replay approved proof steps` |

Sprint acceptance: validated findings have reproducible PoC steps, sensitive proof material stays classified, retest steps are safe, and replay rechecks policy.

## Sprint 24: Validated Finding Packages and Professional Assessment Reporting

Goal: convert only validated findings into professional finding packages and campaign assessment reports suitable for bug bounty triage, internal AppSec review, external client assessment, executive review, and engineering remediation.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 24.1 reportable finding schema | Define required fields for report-ready validated findings | Missing scope, evidence, reproduction, impact, or validation fails | `pytest tests/test_reportable_finding_schema.py` | schema fixture | `src/aotp/reportable_finding.py` | `define reportable finding schema` |
| 24.2 audience-specific packages | Generate bug bounty, internal AppSec, executive, developer, and audit archive views | All views derive from the same validated finding | `pytest tests/test_audience_report_packages.py` | report package fixtures | `src/aotp/report_package.py`, templates | `generate professional finding packages` |
| 24.3 evidence appendix | Generate appendix with artifact paths, SHA256 hashes, timestamps, redaction notes, and classification | Hashes verify and sensitive annex stays separate | `pytest tests/test_evidence_appendix.py` | appendix artifact | `src/aotp/evidence_appendix.py` | `add report evidence appendix` |
| 24.4 no-finding assessment report | Generate professional no-finding due-diligence report from completed campaign evidence | Report includes tested, untested, skipped, denied, and limitations | `pytest tests/test_no_finding_report.py` | no-finding report | templates and report modules | `generate no finding assessment reports` |
| 24.5 report quality gate | Block incomplete, unsupported, out-of-scope, duplicate, or unvalidated findings | Only validated report-ready findings export | `pytest tests/test_report_quality_gate.py` | quality gate verdicts | `src/aotp/report_quality_gate.py` | `gate professional report quality` |
| 24.6 remediation guidance | Produce scoped remediation and safe retest guidance without unsupported root-cause claims | Guidance cites evidence and limitations | `pytest tests/test_remediation_guidance.py` | remediation section | `src/aotp/remediation_guidance.py` | `add scoped remediation guidance` |
| 24.7 manual disclosure package | Export manual-only packages for HackerOne, Bugcrowd, client delivery, or internal review | No automatic external submission path exists | `pytest tests/test_manual_disclosure_package.py` | package artifact | `src/aotp/disclosure_package.py` | `export manual assessment packages` |
| 24.8 professional campaign summary | Summarize scope, ROE, coverage, agent actions, validated findings, rejected candidates, proof requests, and limitations | Summary is supported by campaign state and evidence | `pytest tests/test_campaign_summary_report.py` | campaign summary | `src/aotp/campaign_summary.py` | `summarize professional campaign results` |

Sprint acceptance: AOTP can create validated finding packages and professional campaign assessment reports for multiple audiences, with evidence hashes, reproduction steps, validation notes, false-positive checks, scope decisions, remediation, limitations, and manual-only disclosure workflows.

## Sprint 25: Campaign Reliability, Replay, Resume, and Agent Orchestration

Goal: make long-running agentic campaigns durable, resumable, replay-safe, and auditable while preserving policy, approval, evidence, vault, and transcript integrity.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 25.1 durable checkpoints | Save campaign, agent, action queue, approvals, and evidence state | Interrupted campaigns resume from verified state | `pytest tests/test_campaign_checkpoints.py` | checkpoint fixture | `src/aotp/checkpoints.py` | `checkpoint agentic campaigns` |
| 25.2 resume engine | Resume campaigns only after state, scope, ROE, and vault authorization revalidate | Changed policy can deny resume | `pytest tests/test_campaign_resume.py` | resume transcript | `src/aotp/resume.py` | `resume campaigns safely` |
| 25.3 replay-safe actions | Give actions stable identities and idempotency rules | Replay cannot duplicate side effects | `pytest tests/test_replay_safe_actions.py` | replay fixture | `src/aotp/replay.py` | `record replay safe actions` |
| 25.4 approval recovery | Recover interrupted human approvals with exact context and identity | Approval context cannot be broadened | `pytest tests/test_approval_recovery.py` | approval evidence | approval modules | `recover approval interrupts` |
| 25.5 agent transcript integrity | Hash agent decisions, tool calls, observations, and report derivation | Transcript tampering is detected | `pytest tests/test_transcript_integrity.py` | transcript hashes | `src/aotp/transcript_integrity.py` | `verify agent transcript integrity` |
| 25.6 LangGraph orchestration hardening | Route assigned agents through durable graph nodes with interrupts and policy boundaries | Graph behavior matches deterministic campaign state | `pytest tests/test_langgraph_orchestration.py` | orchestration fixture | orchestration modules | `harden agent orchestration graph` |
| 25.7 failure recovery | Record failed tool runs without corrupting state and continue when policy allows | Failed action consumes budget and preserves evidence | `pytest tests/test_failed_tool_recovery.py` | failure artifact | campaign loop and tool modules | `recover failed governed tool runs` |

Sprint acceptance: AOTP campaigns can pause, resume, replay approved work, recover approvals, preserve vault authorization, and prove transcript integrity without bypassing current policy.

## Sprint 26: Authorized External Campaign Readiness

Goal: prepare AOTP for controlled, low-noise, authorized external campaigns after local benchmark testing proves agentic execution, evidence validation, finding quality, reporting, and reliability.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 26.1 program policy ingest | Ingest saved HTML, pasted text, Markdown, and PDF policy into a private program profile | Policy provenance and required terms are retained | `pytest tests/test_program_policy_ingest.py` | policy profile fixture | `src/aotp/program_ingest.py` | `ingest authorized program policy` |
| 26.2 scope normalization | Normalize domains, paths, APIs, mobile, exclusions, credentials, rate limits, and test windows | Ambiguity blocks execution until operator decision | `pytest tests/test_scope_normalizer.py` | scope decision matrix | `src/aotp/scope_normalizer.py` | `normalize external program scope` |
| 26.3 low-noise execution profile | Default external campaigns to passive and browser-first actions | Active checks require explicit program permission | `pytest tests/test_low_noise_external_profile.py` | ROE fixture | `src/aotp/external_campaign_mode.py` | `add low noise external campaign mode` |
| 26.4 duplicate and prior-art review | Track known disclosures, previous submissions, and low-value patterns | Duplicate risk is visible before reporting | `pytest tests/test_prior_art_review.py` | review record | `src/aotp/prior_art_review.py` | `review external prior art` |
| 26.5 manual submission gate | Export manual-only submission packages with no auto-submit capability | Missing proof, scope, impact, or evidence blocks export | `pytest tests/test_submission_gate.py` | manual package | `src/aotp/submission_gate.py` | `gate manual external submissions` |
| 26.6 pilot campaign checklist | Generate preflight and postflight checklists for authorized programs or clients | Operator confirms scope, ROE, and reporting destination | `pytest tests/test_pilot_campaign_checklist.py` | checklist artifact | docs and CLI | `add authorized pilot checklist` |

Sprint acceptance: AOTP can prepare an authorized external campaign profile, enforce low-noise ROE, block ambiguity and scope expansion, export manual-only packages, and provide operator checklists. External live use remains operator-controlled and must follow each program or client authorization.

## Long-term release criteria

AOTP is release-ready only when it can demonstrate the following on authorized targets:

- the campaign starts from explicit scope and ROE
- agents create an executable WSTG plan
- tools execute only through governed adapters
- browser workflows preserve state and evidence
- authenticated sessions use provisioned accounts safely
- action chains are controlled and approval-gated
- findings are validated before reporting
- false positives and duplicates are rejected with reasons
- PoC steps are reproducible and safe to retest
- professional report packages are generated for the selected audience
- campaign replay and resume preserve policy and evidence integrity
- all sensitive material remains classified, vaulted, or excluded according to policy

The project succeeds when it can perform diligent, professional, senior-level web application security testing through agentic workflows and produce vetted, validated findings that are useful to program triagers, internal AppSec teams, clients, developers, and executives.
