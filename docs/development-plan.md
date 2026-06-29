# Development plan

This plan builds AOTP as small, reviewable, license-ready slices. The [engineering agent SOP](engineering-agent-sop.md) governs branch, test, commit, and synchronization behavior.

For every slice below, validation includes the listed focused command plus `python3 -m compileall src tests`, `python3 -m pytest`, `./scripts/validate-repository-safety.sh`, and `make test`. Evidence includes command output, focused test names, reviewed diff, and a no-private-material confirmation. Files are the named areas plus adjacent tests and documentation. Every suggested commit message is lowercase.

## Sprint 0: private-safe foundation and repository creation

Goal: create the private repository, package scaffold, policies, proprietary license, redaction controls, CI, and test baseline.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 0.1 repository scaffold and metadata | Create package, README, metadata, ignores, and examples | Fresh checkout installs; examples are inert | `aotp --help` | install and tree output | root, `src/aotp`, `config` | `scaffold repository metadata` |
| 0.2 repository safety validation script | Detect prohibited paths and obvious secret forms | Unsafe fixture fails; repository passes | `./scripts/validate-repository-safety.sh` | pass and negative fixture result | `scripts`, `.gitignore`, tests | `add repository safety validation` |
| 0.3 minimal CLI and config loading | Add argparse commands and fail-closed YAML loading | Valid example loads; malformed input fails | `aotp validate-config --scope config/scope.example.yaml` | CLI JSON output | `cli.py`, `config.py`, config | `add safe cli and config loading` |
| 0.4 fail-closed policy gate | Deny missing authority, scope expansion, unsafe paths, and forbidden actions | Negative tests cover every denial family | `pytest tests/test_policy_gate.py` | denial matrix | `policy_gate.py`, tests | `implement fail closed policy gate` |
| 0.5 CI workflow and validation evidence | Run compile, tests, and safety validation on GitHub | All jobs pass on clean checkout | `make check` | local and Actions result | `.github/workflows`, Makefile | `add continuous validation workflow` |
| 0.6 proprietary license file | Add exact all-rights-reserved terms | No open-source grant or classifier exists | `rg -n "MIT|Apache|GPL|BSD|MPL" LICENSE.md pyproject.toml` | reviewed license diff | `LICENSE.md`, licensing docs | `add proprietary license terms` |

Sprint acceptance: private GitHub repository exists; core policy documents exist; compile, tests, safety, and Make targets pass; worktree is clean.

## Sprint 1: scope, authorization, and rules of engagement

Goal: make live testing possible only with explicit private authority.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 1.1 scope schema and examples | Define aliases, assets, accounts, categories, windows, limits, and evidence rules | Example remains dry-run only | `pytest tests/test_config.py` | schema cases | config model and docs | `define private scope model` |
| 1.2 authorization metadata checks | Require written authorization, agreement, profile, and applicable confidentiality references | Placeholder or missing reference denies live | `pytest tests/test_policy_gate.py -k live` | denial outputs | policy and tests | `require live authorization metadata` |
| 1.3 rules-of-engagement checks | Require confirmation, reference, forbidden actions, and stop rules | Missing confirmation denies live | `pytest tests/test_policy_gate.py -k rules` | focused results | policy, scope docs | `enforce rules of engagement` |
| 1.4 live mode approval checks | Require live flag plus operator and objective approvals | Example scope cannot run live | `aotp run-case --scope config/scope.example.yaml --case cases/wstg-security-headers.example.yaml --live --operator-approved` | expected denial | CLI, human approval | `gate live execution approvals` |
| 1.5 negative fail-closed tests | Cover target, service, API, category, time, and evidence violations | Each missing field has a deterministic denial | `pytest tests/test_policy_gate.py` | denial matrix | tests and fixtures | `expand policy denial coverage` |

Sprint acceptance: live mode cannot use examples; target expansion and forbidden actions are denied; tests prove every critical denial.

## Sprint 2: campaign loop and campaign state

Goal: implement bounded scheduling, checkpoints, events, stop conditions, pause, and resume.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 2.1 campaign file parser | Parse named objectives and limits | Empty or malformed campaigns fail | `pytest tests/test_campaign_loop.py` | parser cases | `campaign.py`, campaigns | `add campaign parser` |
| 2.2 campaign state model | Persist required identity, disposition, counter, and stop fields | Round trip preserves all fields | `pytest tests/test_campaign_state.py` | state fixture | `campaign_state.py` | `add campaign state model` |
| 2.3 campaign loop skeleton | Gate each objective and write outcome evidence | Every iteration has evidence or policy stop | `pytest tests/test_campaign_loop.py` | event and evidence paths | `campaign_loop.py` | `implement bounded campaign loop` |
| 2.4 scheduler and safety budget | Order approved work and enforce iteration, runtime, and requests | No budget can be exceeded | `pytest tests/test_safety_budget.py` | boundary cases | scheduler and budget | `enforce campaign safety budgets` |
| 2.5 pause resume and stop behavior | Add operator stop and reviewed resume state | Invalid resume fails; stop persists | `aotp campaign-stop --state <fixture>` | before and after state | CLI and state | `add campaign pause resume and stop` |
| 2.6 campaign event log | Record iteration, policy, module, outcome, and evidence | Events are ordered and complete | `pytest tests/test_campaign_loop.py -k events` | event JSON | loop and state | `record structured campaign events` |
| 2.7 LangGraph orchestration prototype | Map approved objectives to nodes, add a durable checkpointer and interrupts, and preserve the policy boundary | Restart, pause, approval, denial, and resume match the deterministic state contract | `pytest tests/test_langgraph_orchestration.py` | checkpoint and parity fixtures | orchestration adapter, state, tests, dependency inventory | `prototype durable langgraph orchestration` |

Sprint acceptance: plan and dry-run work; state tracks all dispositions; stop conditions and reviewed resume are enforced; the LangGraph prototype passes state and policy parity tests before it can replace the initial loop.

## Sprint 3: evidence and finding candidate pipeline

Goal: hash, redact, verify, classify, and report without invented facts.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 3.1 evidence manifest model | Implement required campaign, authorization, mapping, artifact, and verdict fields | Invalid verdict or redaction fails | `pytest tests/test_evidence_manifest.py` | manifest fixture | `evidence.py` | `define evidence manifest contract` |
| 3.2 redaction checks | Detect secrets and personal identifiers at boundaries | All required secret classes are blocked | `pytest tests/test_redaction.py` | parameter results | `redaction.py` | `enforce evidence redaction` |
| 3.3 evidence hashing | Hash artifacts and verify identity | Modified artifact fails verification | `pytest tests/test_evidence_manifest.py -k hash` | expected digests | evidence code | `add evidence artifact hashing` |
| 3.4 verifier verdict model | Restrict verdicts to five values | Unsupported value fails | `pytest tests/test_evidence_manifest.py` | negative result | `verifier.py` | `restrict verifier verdicts` |
| 3.5 finding candidate model | Separate severity, confidence, strength, and human validation | No candidate exists without evidence | `pytest tests/test_finding_candidate.py tests/test_finding_lifecycle.py` | lifecycle cases | finding modules | `add evidence bound finding lifecycle` |
| 3.6 markdown report generator | Render evidence fields only | No unsupported impact or remediation appears | `pytest tests/test_reporter.py` | generated report | `reporter.py` | `generate evidence only reports` |

Sprint acceptance: hashes verify, redaction fails closed, candidates are evidence-bound, and reports do not invent facts.

## Sprint 4: WSTG web application module

Goal: provide safe WSTG case models and dry-run adapter contracts.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 4.1 WSTG case registry | Register version-aware case mappings | `list-cases` exposes approved cases | `aotp list-cases` | registry output | cases and module | `add wstg case registry` |
| 4.2 authentication and session cases | Model provisioned-account authn and sessions | No credential guessing action exists | `aotp run-case ... --dry-run` | dry-run evidence | authn case files | `add safe authn session cases` |
| 4.3 authorization cross-account case | Require human approval for cross-account confirmation | Unapproved case pauses or denies | `pytest tests/test_policy_gate.py -k human` | denial record | authz case and approval | `gate cross account testing` |
| 4.4 security header case | Model observation-only header review | No mutation or crawl occurs | run header case dry-run | evidence manifest | header case | `add security header case` |
| 4.5 browser-agent context case | Model DOM, screenshot, and browser context placeholders | Artifacts stay local and redacted | run browser case dry-run | placeholder references | browser cases | `add browser context evidence case` |
| 4.6 adapter stubs | Define Playwright, ZAP, mitmproxy, OSMAP, and browser-suite contracts | Stubs declare supports, requires, denies | `pytest tests/test_capability_registry.py` | registry output | adapters and docs | `add web adapter contracts` |

Sprint acceptance: WSTG cases list and dry-run; mappings enter evidence; adapters remain optional and network-silent.

## Sprint 5: service control panel misconfiguration

Goal: safely assess explicitly scoped management interfaces.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 5.1 panel target model | Define explicit panel aliases and categories | Unlisted panel is denied | focused policy test | denial evidence | scope and panel module | `define control panel targets` |
| 5.2 safe checks | Model headers, TLS, login exposure, versions, defaults, indexing, and metadata | Credential and destructive actions absent | module contract test | capability output | panel module and cases | `add safe panel observations` |
| 5.3 panel evidence | Add panel-specific metadata placeholders | Dry-run creates redacted evidence | run panel case dry-run | manifest | evidence and module | `record panel evidence` |
| 5.4 lockout stop conditions | Detect or flag lockout and unsafe actions | Risk pauses before execution | approval and policy tests | pause event | approval and loop | `stop on panel lockout risk` |
| 5.5 report mapping | Render only captured panel fields | No candidate without evidence | reporter test | report excerpt | reporter and docs | `map panel evidence to reports` |

Sprint acceptance: unscoped panels and credential attacks are refused; dry-run evidence is safe; reports remain evidence-bound.

## Sprint 6: bounded fuzzing

Goal: enforce explicit authorization, small budgets, safe payload classes, and instability stops.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 6.1 fuzzing authorization | Require category and action approval | Default scope denies fuzzing | policy fuzzing test | denial record | policy and scope | `require fuzzing authorization` |
| 6.2 payload budget | Define payload classes and count | Zero or missing budget denies | focused budget test | boundary cases | fuzz module | `bound fuzzing payloads` |
| 6.3 endpoint budget | Enforce per-endpoint and total requests | Counter cannot exceed limits | budget tests | counter state | budget and loop | `bound fuzzing requests` |
| 6.4 corpus reference | Hash and reference private corpus without committing it | Evidence contains reference, not payload secrets | evidence test | manifest | evidence and fuzz module | `record fuzzing corpus references` |
| 6.5 dry-run execution | Plan requests without sending them | Request count remains zero | run fuzz case dry-run | dry-run evidence | executor and module | `add network silent fuzz dry run` |
| 6.6 instability stops | Stop on size, retry, runtime, instability, or lockout signals | Stop event and counters persist | focused loop tests | stop history | loop and budget | `stop unsafe fuzzing conditions` |

Sprint acceptance: fuzzing requires explicit authority and budgets; state-changing behavior is separately gated; counters and stops are proven.

## Sprint 7: SBOM and dependency review

Goal: review only provided artifacts while separating presence from exploitability.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 7.1 artifact ingestion | Accept and hash provided SBOMs and manifests | Unprovided path is denied | policy artifact test | hash and denial | SBOM module and policy | `ingest provided dependency artifacts` |
| 7.2 package evidence | Record package, version, source, and hash | Evidence is reproducible | manifest test | package record | SBOM and evidence | `record component evidence` |
| 7.3 vulnerability mapping interface | Define configured data-source contract | No implicit external lookup occurs | adapter contract test | interface output | SBOM adapter | `add vulnerability mapping contract` |
| 7.4 reachability caveat | Track presence, reachability, and exploitability separately | Presence cannot become confirmed risk alone | finding tests | lifecycle result | finding and SBOM | `separate component presence from risk` |
| 7.5 SBOM report section | Render recorded component facts and caveats | No unsupported exploitation claim | reporter test | report excerpt | reporter | `add evidence only sbom reporting` |

Sprint acceptance: provided artifacts are represented and hashed; non-provided inputs are denied; reports distinguish presence from confirmed risk.

## Sprint 8: cryptographic controls review

Goal: review scoped observable or provided cryptographic evidence safely.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 8.1 TLS certificate evidence | Model protocol and certificate metadata | Raw private material is absent | evidence test | TLS fixture | crypto module | `record tls certificate evidence` |
| 8.2 cookie attributes | Record transport-related attributes without values | Cookie values trigger redaction | redaction test | safe fixture | crypto and redaction | `review cookie security attributes` |
| 8.3 token configuration | Review provided algorithm and validation settings | Tokens and secrets are blocked | focused redaction test | config fixture | crypto module | `review provided token configuration` |
| 8.4 weak algorithm indicators | Keep indicators distinct from confirmed weakness | Human review required for finding | lifecycle test | candidate state | crypto and finding | `model weak algorithm indicators` |
| 8.5 key management artifacts | Review provided metadata, never key material | Private-key marker fails closed | redaction test | denial output | crypto and policy | `gate key management evidence` |
| 8.6 crypto report section | Render observed evidence and uncertainty | No brute force or unverified claim | reporter test | report excerpt | reporter | `add cryptographic evidence reporting` |

Sprint acceptance: extraction and brute force are refused; weaknesses require evidence; reports preserve uncertainty.

## Sprint 9: Ollama planner, verifier, and report assistant

Goal: use local structured models without giving them authority or secrets.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 9.1 Ollama config model | Add localhost default and approved models | Remote endpoint is not default | config test | parsed config | model config | `configure local ollama models` |
| 9.2 structured JSON adapter | Use JSON output and timeouts | Invalid response fails gracefully | adapter unit test | mocked response | Ollama adapter | `add structured ollama adapter` |
| 9.3 planner schema | Restrict suggestions to approved objective IDs | Unknown objective is rejected | planner test | rejection result | planner | `constrain model planning suggestions` |
| 9.4 verifier schema | Restrict model assistance to evidence summaries | Model cannot set authorization | verifier test | schema result | verifier and adapter | `constrain model verification assistance` |
| 9.5 secret stripping | Sanitize every prompt recursively | Required secret classes never reach body | `pytest tests/test_redaction.py` | sanitized prompt | redaction and adapter | `strip secrets from model prompts` |
| 9.6 no-secret tests | Add nested payload and regression cases | Prompt construction fails safe | focused adapter tests | negative cases | tests | `prove model prompt redaction` |

Sprint acceptance: localhost and structured output are defaults; suggestions cannot bypass policy; secrets do not enter prompts; unavailable Ollama is bounded.

## Sprint 10: live adapter readiness

Goal: define testable contracts for future live tools without enabling them by default.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 10.1 Playwright contract | Define navigation, DOM, screenshot, and trace capabilities | Scope and rate requirements declared | capability test | registry entry | Playwright adapter | `define playwright adapter contract` |
| 10.2 ZAP contract | Define passive and limited spider capabilities | Active scan denied without approval | capability test | registry entry | ZAP adapter | `define zap adapter contract` |
| 10.3 mitmproxy contract | Define authorized capture and redaction boundary | Unscoped interception denied | capability test | registry entry | proxy adapter | `define mitmproxy adapter contract` |
| 10.4 OSMAP contract | Bridge explicit local cases and evidence references | No code vendoring or implicit live run | provenance review | reviewed diff | OSMAP adapter and docs | `define osmap adapter contract` |
| 10.5 browser-suite contract | Bridge external browser evidence | Separate license obligations documented | license review | inventory note | browser adapter and docs | `define browser suite adapter contract` |
| 10.6 placeholder integration examples | Demonstrate dry-run wiring with aliases only | No real target or private data exists | safety validator | safe examples | examples and docs | `add safe adapter examples` |

Sprint acceptance: contracts are documented and testable; live use requires private scope; no private material or copied code is committed.

## Sprint 11: candidate evaluation demonstration

Goal: produce a polished, network-silent private demonstration release.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 11.1 demo script | Document a repeatable evaluator walkthrough | Fresh clone steps work | follow demo script | terminal record | demo docs | `add evaluator demo script` |
| 11.2 sample dry-run output | Generate clearly marked placeholders | Output is reproducible and inert | campaign dry-run | local ignored output | examples and docs | `document dry run campaign output` |
| 11.3 example report | Generate from placeholder evidence only | Report states its limitations | reporter command | report sample | reporter docs | `add placeholder evidence report` |
| 11.4 architecture review | Review authority and data flows | No bypass path exists | threat-model checklist | review record | architecture docs | `review campaign architecture` |
| 11.5 repository safety review | Audit tracked inventory and history | No prohibited material is found | safety validator and `git grep` | audit record | repository-wide | `complete repository safety review` |
| 11.6 v0.1 checklist | Verify install, docs, policy, tests, and license | Every release item passes | `make check` | release checklist | release docs | `prepare private v0.1 release` |

Sprint acceptance: demo works from a fresh clone without live traffic; placeholder report is clear; safety passes; release checklist is complete.

## Sprint 12: bug bounty operator workflow

Goal: support private profiles, duplicate control, human-reviewed report packages, and privacy-safe metrics.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 12.1 private program profile | Implement separate private policy context | Live campaign lacks authority without it | profile policy test | denial record | profile model | `add private program profiles` |
| 12.2 policy checklist | Record acceptance, safe harbor, disclosure, and stops | Missing required term denies | checklist test | completed placeholder | profile docs | `add program policy checklist` |
| 12.3 scope enforcement | Enforce in-scope, out-of-scope, and prohibited actions | Out-of-scope aliases deny | policy tests | denial matrix | policy | `enforce program scope boundaries` |
| 12.4 duplicate tracking | Add private prior-test fingerprints and outcomes | Memory is ignored and alias-only | memory test | schema fixture | campaign memory | `add duplicate avoidance memory` |
| 12.5 report package | Bundle redacted evidence references and draft | Package is marked draft | reporter test | package manifest | reporter | `build human reviewed report package` |
| 12.6 submission gate | Require human approval and keep submission manual | No automatic submission path exists | approval test | pause event | approvals and docs | `gate report submission` |
| 12.7 efficiency metrics | Track time, counts, outcomes, bounty, and cost separately | Metrics contain no target data | metrics test | aggregate fixture | metrics | `add private operator metrics` |

Sprint acceptance: real profiles remain private; out-of-scope and prohibited actions deny; drafts require human review; no submission automation exists.

## Sprint 13: licensing and commercialization readiness

Goal: prepare for private licensing, evaluator access, commercialization, or a later carefully reviewed release.

| Slice | Implementation tasks | Acceptance checks | Focused validation | Evidence | Files likely touched | Commit suggestion |
|---|---|---|---|---|---|---|
| 13.1 proprietary license | Verify all-rights-reserved terms and metadata | No open-source grant is present | license grep | reviewed license | license and metadata | `confirm proprietary licensing` |
| 13.2 dependency inventory | Record direct, dev, transitive, and tooling obligations | Every dependency has a review status | package metadata review | inventory | dependency docs | `inventory dependency licenses` |
| 13.3 attribution policy | Define provenance and clean-room integration rules | Unclear code cannot merge | contribution checklist | provenance record | contributing docs | `define third party attribution policy` |
| 13.4 evaluator model | Draft limited evaluation rights and restrictions | Draft is marked for legal review | document review | review notes | evaluator license doc | `draft evaluator license model` |
| 13.5 commercialization checklist | Cover rights, support, privacy, retention, and release terms | Owners and open items are visible | checklist review | readiness record | commercialization docs | `add commercialization readiness checklist` |
| 13.6 public release risk review | Audit history, secrets, licenses, claims, and private artifacts | Release is blocked until all risks close | safety and history audit | signed review record | repository-wide | `add public release risk review` |

Sprint acceptance: repository remains private and proprietary; dependency and future-license options are documented; no private assessment material is prepared for release.

## Branch and closeout convention

Development uses `sprint/<number>-<short-name>` and, when useful, `slice/<number>.<number>-<short-name>`. Each completed slice is tested, committed with its lowercase suggestion or an equally precise message, pushed, reviewed, and integrated. Sprint closeout synchronizes `origin/main`, confirms the remote commit and repository visibility, and leaves the worktree clean.
