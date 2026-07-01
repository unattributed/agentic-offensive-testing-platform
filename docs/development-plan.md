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
| 5.4 report review gating | Require a manifest-bound human review record before panel candidate creation | Candidate and report gates fail closed | review-gate tests | review decision record | candidate, reporter, and CLI | `add report review gating` |
| 5.5 lockout stop conditions and campaign integration | Detect explicit lockout-risk signals and support panel campaign objectives | Risk pauses before execution; campaign evidence stays network-silent | approval, campaign, and policy tests | pause event and panel evidence | campaign, approval, loop, and panel module | `stop on panel lockout risk` |
| 5.6 report mapping and closeout | Render only validated fields from the hashed panel evidence artifact | No panel candidate without manifest-bound review; report re-derives the gate | adversarial reporter and end-to-end tests | report excerpt and validation record | reporter, tests, and docs | `map panel evidence to reports` |

Sprint acceptance: unscoped panels and credential attacks are refused; dry-run evidence is safe; reports remain evidence-bound.

Plan amendment: the initial plan assigned lockout stop conditions to 5.4 and report mapping to
5.5. PR #10 used 5.4 for report-review gating before those planned items were implemented. The
amended sequence preserves that published history, moves lockout and campaign work to 5.5, and
moves report mapping and adversarial closeout to 5.6. No original acceptance requirement is
removed.

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

Sprint acceptance: source remains proprietary, operational material remains private, dependency
and future-license options are documented, and commercial, evaluator, and open-source distribution
remain blocked until every recorded review closes.

Plan correction: repository visibility is public, not private. Sprint 13 preserves proprietary
source terms and private operations without claiming that repository visibility is private.

## Sprint 14: Ollama Deep Agent Campaign Runtime

Goal: build the first real agentic campaign loop using local Ollama plus LangChain Deep Agents,
with no MCP. The agent plans, calls governed native tools, analyzes evidence summaries, and chooses
the next test.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 14.1 | Bootstrap Ollama Deep Agent and validate the local model | Ollama is detected on `127.0.0.1` only; configured model is available |
| 14.2 | Create `.aotp/campaigns/<program>/<run-id>/` bounded workspace | State and artifacts cannot escape the workspace |
| 14.3 | Define Deep Agent supervisor and subagents | Supervisor and delegated roles start with bounded context |
| 14.4 | Define structured test-objective and tool-call proposal schema | Agent emits valid structured proposal JSON |
| 14.5 | Gate model-proposed objectives | Malformed and out-of-scope proposals are denied |
| 14.6 | Add HTTP metadata, TLS metadata, robots, and security.txt native tools | Approved metadata tools execute; no unregistered tool path exists |
| 14.7 | Return classified evidence summaries to the agent | Evidence is written, hashed, classified, and summarized |
| 14.8 | Run a three-iteration campaign loop | Agent analyzes each summary and completes at least three iterations |
| 14.9 | Demonstrate a no-credential campaign on an authorized owned target | Live proof remains in scope and produces a due-diligence result |
| 14.10 | Document the sprint and operator demo | Report draft or no-finding summary is generated; no MCP code path exists |

Development evidence: `src/aotp/deep_agent/bootstrap.py`,
`src/aotp/deep_agent/supervisor.py`, `src/aotp/deep_agent/subagents.py`,
`src/aotp/agent_workspace.py`, `src/aotp/agentic_campaign_loop.py`,
`src/aotp/model_proposals.py`, `src/aotp/model_proposal_gate.py`,
`src/aotp/agent_tools/http_metadata.py`, `src/aotp/agent_tools/tls_metadata.py`,
`src/aotp/evidence_summarizer.py`, `docs/sprint-14-ollama-deep-agent-runtime.md`,
`scripts/run-sprint14-agentic-mailhost-demo.sh`, `tests/test_agent_workspace.py`,
`tests/test_model_proposals.py`, `tests/test_model_proposal_gate.py`, and
`tests/test_agentic_campaign_loop.py`.

Sprint acceptance: the local supervisor produces governed structured proposals, approved metadata
tools execute, evidence feeds the next decision for at least three iterations, output is
evidence-linked, and no MCP path exists.

## Sprint 15: Campaign-Governed Native Tool Registry

Goal: make every real tool typed, risk-tiered, scoped, budgeted, logged, classified, and approved
under human-defined ROE.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 15.1 | Implement the native tool registry | Agent requests map only to registered tools |
| 15.2 | Define risk tiers from passive metadata to exploitation validation | Every tool call resolves to a documented risk tier |
| 15.3 | Add ROE-driven tool permissions | Tools not allowed by ROE are denied |
| 15.4 | Enforce request budgets and rate limits | Over-budget calls are denied before execution |
| 15.5 | Add a constrained Parrot campaign shell | Shell cannot run arbitrary commands |
| 15.6 | Add a single-host, single-service governed nmap wrapper | Arguments and targets outside scope are denied |
| 15.7 | Add an OWASP ZAP passive baseline wrapper | Approved passive execution is bounded and captured |
| 15.8 | Add a Playwright passive browser metadata wrapper | Browser collection remains scoped and classified |
| 15.9 | Record denied calls as campaign evidence | Denial reason and proposal are evidence-bound |
| 15.10 | Generate a FOSS tool inventory | Availability never grants authority |

Development evidence: `src/aotp/tool_registry.py`, `src/aotp/tool_risk_tiers.py`,
`src/aotp/roe.py`, `src/aotp/request_budget.py`,
`src/aotp/agent_tools/campaign_shell.py`, `src/aotp/agent_tools/nmap_governed.py`,
`src/aotp/agent_tools/zap_passive.py`, `src/aotp/agent_tools/playwright_passive.py`,
`src/aotp/tool_inventory.py`, `docs/sprint-15-campaign-governed-tools.md`,
`tests/test_tool_registry.py`, `tests/test_tool_risk_tiers.py`,
`tests/test_request_budget.py`, `tests/test_campaign_shell.py`,
`tests/test_nmap_governed.py`, and `tests/test_zap_passive.py`.

Sprint acceptance: approved FOSS tools execute within scope and budget, denied calls become
evidence, arbitrary shell execution is impossible, and results returned to the agent follow ROE
and evidence classification.

## Sprint 16: Sensitive Evidence Vault and PoC Material Handling

Goal: encrypt sensitive campaign proof, allow authorized agent and tool use during campaign
iterations, support PoC construction, and prevent leakage into normal evidence, git, or reports.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 16.1 | Define `public`, `restricted`, `secret`, `poc_sensitive`, `recipient_only`, and `do_not_store` | Secret-like output is classified automatically |
| 16.2 | Implement encrypted campaign-sensitive storage | Sensitive material is encrypted before persistence |
| 16.3 | Add vault handles across campaign iterations | Normal evidence references handles without raw values |
| 16.4 | Store campaign keys, hashes, passwords, tokens, private keys, and proof material | Authorized campaign material persists safely |
| 16.5 | Enforce authorized raw agent access | Access denies outside active campaign ROE |
| 16.6 | Add secret-bearing in-memory tool interfaces | Approved tools use material without argv or log leakage |
| 16.7 | Add a classified PoC workspace | Vault-backed material can build reproducible proof |
| 16.8 | Implement sensitive annex export | Annex stays separate from the normal report |
| 16.9 | Block unencrypted vault leakage in repository safety | Tracked plaintext sensitive material fails validation |
| 16.10 | Gate vault export, report inclusion, and campaign handoff | Each action requires explicit human approval |

Development evidence: `src/aotp/evidence_classifier.py`, `src/aotp/sensitive_vault.py`,
`src/aotp/vault_handles.py`, `src/aotp/campaign_key_store.py`,
`src/aotp/agent_vault_access.py`, `src/aotp/secret_bearing_tools.py`,
`src/aotp/poc_workspace.py`, `src/aotp/sensitive_annex.py`,
`src/aotp/report_export_policy.py`, `scripts/validate-vault-leakage.sh`,
`docs/sprint-16-sensitive-evidence-vault.md`, `tests/test_evidence_classifier.py`,
`tests/test_sensitive_vault.py`, `tests/test_vault_handles.py`,
`tests/test_campaign_key_store.py`, `tests/test_agent_vault_access.py`,
`tests/test_secret_bearing_tools.py`, and `tests/test_sensitive_annex.py`.

Sprint acceptance: every raw read logs purpose, handle, campaign, and identity; authorized agent
and tool use works; normal evidence, terminal logs, git, and public reports exclude raw material;
retention and export rules hold; and annex export requires approval.

## Sprint 17: WSTG Campaign Coverage Engine

Goal: generate WSTG-aligned campaign phases, track coverage and gaps, and let the agent choose the
next approved test from evidence.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 17.1 | Define a WSTG strategy map with executable families | Mappings are version-aware and evidence-linked |
| 17.2 | Define passive, browser, auth, input, validation, and report phases | Every objective belongs to a campaign phase |
| 17.3 | Generate WSTG objectives from scope and ROE | Generated objectives remain in scope |
| 17.4 | Track coverage and analyze gaps | Status includes tested, skipped, denied, blocked, and deferred |
| 17.5 | Add auth boundary checks | Only approved checks execute |
| 17.6 | Add session management checks | Session material follows classification policy |
| 17.7 | Add error and input-boundary checks | Budgets and stop conditions apply |
| 17.8 | Add browser route and form metadata checks | Browser evidence links to WSTG categories |
| 17.9 | Let the agent choose the next objective from evidence gaps | Agent explains the next choice |
| 17.10 | Generate a WSTG coverage report | Report explains continue or stop reasoning |

Development evidence: `src/aotp/wstg/strategy_map.py`,
`src/aotp/wstg/objective_generator.py`, `src/aotp/wstg/coverage.py`,
`src/aotp/wstg/auth_boundary.py`, `src/aotp/wstg/session_management.py`,
`src/aotp/wstg/error_handling.py`, `src/aotp/wstg/input_boundary.py`,
`src/aotp/wstg/browser_metadata.py`, `docs/sprint-17-wstg-campaign-coverage.md`,
`tests/test_wstg_strategy_map.py`, `tests/test_wstg_objective_generator.py`,
`tests/test_wstg_coverage.py`, `tests/test_wstg_auth_boundary.py`, and
`tests/test_wstg_session_management.py`.

Sprint acceptance: WSTG objectives derive from scope and ROE, execution stays approved, coverage
dispositions are explicit, evidence maps back to categories, and the agent explains continuation
or stop.

## Sprint 18: Authenticated OSMAP and Clearbox Workflow

Goal: productize authenticated, metadata-safe, source-informed testing of owned or authorized
targets.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 18.1 | Add interactive credential and TOTP prompts | Values never enter argv, history, or public evidence |
| 18.2 | Define the authenticated session boundary | Active authorization is required |
| 18.3 | Classify and route cookies, CSRF values, and tokens | ROE selects vaulted or memory-only handling |
| 18.4 | Review an OSMAP local repository or zip | Source remains local and produces safe metadata |
| 18.5 | Build source-derived route and auth maps | Maps contain routes and auth requirements |
| 18.6 | Generate OSMAP WSTG candidates | Hints do not grant execution authority |
| 18.7 | Execute governed authenticated route checks | Classified evidence is produced |
| 18.8 | Verify logout and post-logout boundaries | Cleanup and invalidated-session behavior are recorded |
| 18.9 | Review candidate findings agentically | Candidates remain evidence-bound |
| 18.10 | Build the authenticated campaign package | Draft includes evidence references and limitations |

Development evidence: `src/aotp/credential_prompt.py`, `src/aotp/auth_session.py`,
`src/aotp/csrf.py`, `src/aotp/session_evidence.py`,
`src/aotp/integrations/osmap_source_review.py`,
`src/aotp/integrations/osmap_route_map.py`,
`src/aotp/integrations/osmap_wstg_mapper.py`,
`src/aotp/agent_tools/osmap_authenticated_wstg.py`,
`docs/sprint-18-authenticated-osmap-clearbox.md`,
`tests/test_credential_prompt.py`, `tests/test_auth_session.py`,
`tests/test_session_evidence_redaction.py`, `tests/test_osmap_source_review.py`, and
`tests/test_osmap_route_map.py`.

Sprint acceptance: credentials and session material follow campaign storage policy, source input
produces route and auth maps, authenticated work requires authorization, logout boundaries are
verified, and findings cite classified evidence.

## Sprint 19: Bug Bounty Program Mode

Goal: ingest HackerOne or Bugcrowd policy, normalize scope, block ambiguity, run low-noise
campaigns under program rules, and export a manually submitted draft.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 19.1 | Ingest saved HTML, pasted text, Markdown, and PDF policy | Each format creates a private profile |
| 19.2 | Build a normalized program profile | Required policy terms and provenance are retained |
| 19.3 | Normalize assets, domains, paths, APIs, mobile, and exclusions | In-scope and out-of-scope assets are separate |
| 19.4 | Block ambiguous policy pending operator decision | Ambiguity prevents live execution |
| 19.5 | Add bug bounty ROE templates | Templates default to low-noise work |
| 19.6 | Build campaigns from profile and scope | Agent cannot add targets |
| 19.7 | Implement passive and browser-first execution profile | Active scanning requires explicit permission |
| 19.8 | Add duplicate and prior-art review | Duplicate or low-value work is flagged |
| 19.9 | Gate report acceptance quality | Required asset, proof, impact, limits, evidence, and scope exist |
| 19.10 | Export manual-only submission packages | No automatic submission path exists |

Development evidence: `src/aotp/program_ingest.py`,
`src/aotp/policy_document_parser.py`, `src/aotp/pdf_policy_parser.py`,
`src/aotp/program_profile_builder.py`, `src/aotp/scope_normalizer.py`,
`src/aotp/policy_ambiguity.py`, `src/aotp/bug_bounty_mode.py`,
`src/aotp/campaign_builder.py`, `src/aotp/report_acceptance.py`,
`src/aotp/submission_gate.py`, `docs/sprint-19-bug-bounty-program-mode.md`,
`examples/programs/mock-hackerone-program.yaml`,
`examples/roe/bug-bounty-low-noise.yaml`, `tests/test_program_ingest.py`,
`tests/test_pdf_policy_parser.py`, `tests/test_scope_normalizer.py`,
`tests/test_policy_ambiguity.py`, `tests/test_bug_bounty_campaign_builder.py`, and
`tests/test_report_acceptance.py`.

Sprint acceptance: all four policy formats work, ambiguity and scope expansion deny, defaults are
low-noise, active work requires permission, and only a complete manual submission package is
exported.

## Sprint 20: Internal SOW and Enterprise AppSec Mode

Goal: support authorized clearbox, graybox, authenticated, source-informed, stronger-tool,
exploitation-validation, remediation, and attack-path replay workflows under an internal SOW.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 20.1 | Define the SOW profile schema | Authority, environments, controls, and provenance validate |
| 20.2 | Ingest PDF, Markdown, saved HTML, and pasted text | Every format creates a private SOW profile |
| 20.3 | Model production, staging, lab, and safe-exploit environments | Each environment has distinct tool tiers |
| 20.4 | Add stronger internal ROE tiers | High-risk tools need approval unless exactly pre-authorized |
| 20.5 | Ingest local source repositories | Source-derived hints remain within scope |
| 20.6 | Ingest OpenAPI and GraphQL documentation | API candidates retain schema provenance |
| 20.7 | Add a targeted OWASP ZAP active wrapper | High-friction policy approval is mandatory |
| 20.8 | Add controlled input probing and validation wrappers | Arguments, budgets, and stops are enforced |
| 20.9 | Verify remediation and replay approved attack paths | Replay stays in the approved environment |
| 20.10 | Build an internal stakeholder package | Report includes guidance and verification status |

Development evidence: `src/aotp/sow_profile.py`, `src/aotp/sow_ingest.py`,
`src/aotp/environment_model.py`, `src/aotp/internal_testing_mode.py`,
`src/aotp/source_review.py`, `src/aotp/api_schema_ingest.py`,
`src/aotp/agent_tools/zap_active_targeted.py`,
`src/aotp/agent_tools/input_probe.py`, `src/aotp/remediation_verification.py`,
`src/aotp/attack_path_replay.py`, `docs/sprint-20-internal-sow-mode.md`,
`examples/roe/internal-staging-authorized.yaml`, `tests/test_sow_profile.py`,
`tests/test_sow_ingest.py`, `tests/test_environment_model.py`,
`tests/test_zap_active_targeted_policy.py`,
`tests/test_remediation_verification.py`, and `tests/test_attack_path_replay.py`.

Sprint acceptance: all four SOW formats work, environment-specific permissions hold, high-risk
tools and replay are governed, remediation evidence links to the original finding, and the
internal report includes guidance and verification state.

## Sprint 21: Agentic Finding Validation and PoC Builder

Goal: turn raw evidence into high-confidence findings by requesting missing proof, rejecting false
positives, building classified PoCs, and generating reproducible stakeholder-ready steps.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 21.1 | Define the candidate finding model | Every candidate is evidence-bound |
| 21.2 | Define confidence and evidence sufficiency rules | Missing proof blocks confirmation |
| 21.3 | Add the agentic finding review loop | Agent requests proof instead of overclaiming |
| 21.4 | Build safe PoCs with workspace and vault material | Authorized vault material is classified correctly |
| 21.5 | Add an impact analysis helper | Impact is limited to supported evidence |
| 21.6 | Add false-positive rejection | Rejection records reasons and evidence |
| 21.7 | Integrate duplicate memory | Duplicates are blocked or marked low value |
| 21.8 | Build report reproduction steps | Steps are reproducible and evidence-linked |
| 21.9 | Build recipient-specific sensitive annexes | Annex export requires approval |
| 21.10 | Emit a lifecycle dashboard or JSON summary | State moves through candidate, confirmed, ready, or rejected |

Development evidence: `src/aotp/finding.py`, `src/aotp/finding_confidence.py`,
`src/aotp/finding_review.py`, `src/aotp/poc_builder.py`,
`src/aotp/impact_analysis.py`, `src/aotp/false_positive_filter.py`,
`src/aotp/duplicate_memory.py`, `src/aotp/reproduction_steps.py`,
`src/aotp/finding_lifecycle.py`, `docs/sprint-21-agentic-finding-validation.md`,
`tests/test_finding_confidence.py`, `tests/test_poc_builder.py`,
`tests/test_impact_analysis.py`, `tests/test_false_positive_filter.py`,
`tests/test_duplicate_memory.py`, and `tests/test_reproduction_steps.py`.

Sprint acceptance: candidates require sufficient evidence, false positives and duplicates are
handled, authorized vault-backed PoCs remain classified, steps and impact are supported, annexes
are gated, and lifecycle status is explicit.

## Sprint 22: Reporting, Remediation, and Stakeholder Packages

Goal: produce clear, reproducible, scoped, evidence-linked packages for bug bounty triagers and
internal engineering teams, with sensitive material separated.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 22.1 | Add a bug bounty report template | Bug bounty package is generated |
| 22.2 | Add an internal AppSec report template | Internal package is generated |
| 22.3 | Generate an executive summary | Summary remains supported by findings |
| 22.4 | Generate engineering remediation sections | Guidance is scoped to evidence |
| 22.5 | Add an evidence appendix with SHA256 hashes | References and hashes verify |
| 22.6 | Export a sensitive annex | Export is separate and approval-gated |
| 22.7 | Generate no-finding due-diligence reports | Completed work remains evidenced |
| 22.8 | Enforce report quality | Incomplete findings fail |
| 22.9 | Add a manual submission checklist | Automatic disclosure remains blocked |
| 22.10 | Render HTML and Markdown | Both outputs preserve control decisions |

Development evidence: `src/aotp/report_templates.py`,
`src/aotp/report_package.py`, `src/aotp/executive_summary.py`,
`src/aotp/remediation_guidance.py`, `src/aotp/evidence_appendix.py`,
`src/aotp/report_quality_gate.py`, `templates/bug_bounty_report.md`,
`templates/internal_appsec_report.md`, `templates/no_finding_due_diligence.md`,
`docs/sprint-22-reporting-remediation-packages.md`,
`tests/test_report_templates.py`, `tests/test_report_quality_gate.py`, and
`tests/test_sensitive_annex_export.py`.

Sprint acceptance: both report types verify evidence hashes, normal reports exclude vault
material, approved annexes stay separate, incomplete findings fail, no-finding work remains
documented, and submission is manual.

## Sprint 23: Effectiveness Measurement and Agentic Evaluation

Goal: compare static and agentic testing under the same budget and measure evidence quality,
candidate quality, false positives, duplicate avoidance, request efficiency, and report readiness.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 23.1 | Add static-versus-agentic comparison mode | Target, scope, and budget are identical |
| 23.2 | Define campaign metrics | Metrics schema validates |
| 23.3 | Measure request efficiency | Request and budget use compare |
| 23.4 | Measure evidence coverage | Coverage dispositions compare |
| 23.5 | Measure candidate quality | Evidence strength and readiness compare |
| 23.6 | Measure false positives and duplicates | Both are counted explicitly |
| 23.7 | Measure operator and approval time | Manual effort is visible |
| 23.8 | Add OSMAP benchmark fixtures | Benchmarks are reproducible and authorized |
| 23.9 | Generate an HTML metrics report | Results link to campaign evidence |
| 23.10 | Generate a technical stakeholder scorecard | Agentic next-step reasoning is demonstrable |

Development evidence: `src/aotp/campaign_compare.py`, `src/aotp/metrics.py`,
`src/aotp/evaluation.py`, `src/aotp/benchmark_fixtures.py`,
`src/aotp/demo_scorecard.py`, `docs/sprint-23-agentic-effectiveness-evaluation.md`,
`tests/test_campaign_compare.py`, `tests/test_metrics.py`, and
`tests/test_evaluation.py`.

Sprint acceptance: equal-budget runs compare coverage, requests, evidence-linked reasoning,
candidate quality, false positives, duplicates, operator effort, and report readiness in a
technical scorecard.

## Sprint 24: Reliability, Replay, and Campaign Resume

Goal: checkpoint and resume campaigns safely, replay approved actions, preserve authorized vault
context, and prove replay cannot bypass current policy.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 24.1 | Define campaign checkpoints | State stops durably |
| 24.2 | Implement resume | Campaign continues from the verified checkpoint |
| 24.3 | Record replay-safe actions | Stable action identity prevents duplicate side effects |
| 24.4 | Recheck policy on replay | Updated policy can deny a prior action |
| 24.5 | Rehydrate authorized vault access | Access resumes only while authorization remains valid |
| 24.6 | Recover interrupted human approvals | Exact approval context is restored |
| 24.7 | Recover failed tool runs | Failure is recorded without corrupting state |
| 24.8 | Continue the evidence archive | Archive remains complete after resume |
| 24.9 | Hash transcript integrity | Transcript verification detects mutation |
| 24.10 | Simulate crashes and generate replay reports | Stop, resume, and recovery proofs pass |

Development evidence: `src/aotp/checkpoints.py`, `src/aotp/resume.py`,
`src/aotp/replay.py`, `src/aotp/vault_resume.py`,
`src/aotp/transcript_integrity.py`, `docs/sprint-24-reliability-replay-resume.md`,
`tests/test_checkpoints.py`, `tests/test_resume.py`,
`tests/test_replay_policy_recheck.py`, `tests/test_vault_resume.py`, and
`tests/test_transcript_integrity.py`.

Sprint acceptance: campaigns stop and resume, replay rechecks policy, vault authorization is
revalidated, approvals and failed runs recover safely, transcript hashes verify, and evidence
remains complete.

## Sprint 25: Operator Productization and Demo Readiness

Goal: package the CLI, documentation, examples, demos, and safe defaults for bug bounty operators
and internal security teams.

| Slice | Implementation tasks | Acceptance checks |
|---|---|---|
| 25.1 | Add clean agentic campaign CLI commands | Commands validate and remain policy-governed |
| 25.2 | Add a sample bug bounty workflow | Manual submission path is documented |
| 25.3 | Add a sample internal SOW workflow | Stronger ROE and approvals are demonstrated |
| 25.4 | Document Parrot OS setup | FOSS dependencies are reproducible |
| 25.5 | Document local Ollama setup | Endpoint and model validation are clear |
| 25.6 | Add demo mode with sanitized outputs | Demo creates a safe evidence archive |
| 25.7 | Add a technical stakeholder demo script | Agentic value and controls are visible |
| 25.8 | Add quickstart and troubleshooting | Fresh clone setup works |
| 25.9 | Add the agentic MVP release gate | All MVP acceptance checks pass |
| 25.10 | Add versioned release notes | Scope, limits, and evidence are recorded |

Development evidence: `src/aotp/cli.py`, `docs/quickstart-parrot-ollama.md`,
`docs/bug-bounty-operator-workflow.md`, `docs/internal-sow-workflow.md`,
`docs/technical-stakeholder-demo-guide.md`, `examples/campaigns/`,
`examples/roe/`, `scripts/run-agentic-mvp-demo.sh`,
`scripts/release-agentic-mvp-gate.sh`, and
`tests/test_cli_agentic_commands.py`.

Sprint acceptance: fresh-clone Parrot and Ollama setup is documented, one command runs the demo,
sanitized evidence is produced, synthetic vault-backed proof works, the release gate passes, no
MCP dependency exists, and no paid tool is required.

## Branch and closeout convention

Development uses `sprint/<number>-<short-name>` and, when useful, `slice/<number>.<number>-<short-name>`. Each completed slice is tested, committed with its lowercase suggestion or an equally precise message, pushed, reviewed, and integrated. Sprint closeout synchronizes `origin/main`, confirms the remote commit and repository visibility, and leaves the worktree clean.
