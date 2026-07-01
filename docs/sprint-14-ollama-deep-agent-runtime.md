# Sprint 14: Ollama Deep Agent Campaign Runtime

## Result

Sprint 14 adds the first real three-iteration AOTP agentic campaign loop. A LangChain Deep Agent
supervisor uses a tool-capable model served by local Ollama on `127.0.0.1`. The model selects one
approved remaining objective at a time. AOTP validates the structured proposal, executes the exact
registered native tool, hashes and classifies its evidence, and returns a bounded summary for the
next decision.

The Deep Agents package provides execution environment, delegation, steering hooks, and context
management. AOTP keeps authority outside the model. Deep Agents documents that tool boundaries
must enforce security because an agent can do anything its tools allow. Sprint 14 therefore uses
exact objective and argument matching before execution.

No MCP package, configuration, server, client, or runtime path is used.

## Architecture

```text
Ollama on 127.0.0.1
  -> LangChain Deep Agent supervisor
  -> campaign planner, evidence analyst, report drafter subagent definitions
  -> strict ModelProposal
  -> AOTP model proposal gate
  -> HTTP, TLS, or robots/security.txt native metadata tool
  -> private campaign workspace
  -> hashed public-classification evidence summary
  -> next Deep Agent iteration
  -> deterministic due-diligence report
```

The Deep Agent uses an ephemeral state backend. It receives no host shell tool and no campaign
credential. Three purpose-limited subagent definitions establish the delegation boundary for
later campaign growth, while the bounded Sprint 14 loop keeps proposal selection in the supervisor
to avoid unnecessary delegation. Native network execution remains in AOTP functions after policy
acceptance.

## Slices

| Slice | Delivered evidence |
|---|---|
| 14.1 | `deep_agent/bootstrap.py` validates unauthenticated HTTP on `127.0.0.1`, installed model digest, and tool capability |
| 14.2 | `agent_workspace.py` creates mode-0700 campaign directories and mode-0600 atomic artifacts |
| 14.3 | `deep_agent/supervisor.py` and `subagents.py` define the supervisor and three purpose-limited delegates |
| 14.4 | `model_proposals.py` provides a strict Pydantic structured-response contract |
| 14.5 | `model_proposal_gate.py` requires an approved remaining objective, exact tool, exact arguments, target alias, authorization reference, and operator approval |
| 14.6 | `agent_tools/http_metadata.py` and `tls_metadata.py` implement four bounded GET or TLS requests across three tools |
| 14.7 | `evidence_summarizer.py` returns classification, artifact hash, safe observations, and limitations |
| 14.8 | `agentic_campaign_loop.py` completes exactly three iterations and four requests |
| 14.9 | `scripts/run-sprint14-agentic-mailhost-demo.sh` requires an explicit authorized HTTPS origin and operator approval |
| 14.10 | This document and the ignored closeout evidence record the operator workflow and acceptance proof |

## Safety boundaries

- The Ollama control endpoint must be exactly loopback `127.0.0.1`.
- The configured model must be installed and advertise tool-calling support.
- The reference bootstrap uses CPU inference by default to avoid dependence on a GPU or driver.
- The live target is one operator-supplied credential-free HTTPS origin.
- Every proposal must copy an approved objective's tool and arguments exactly.
- Redirects are not followed.
- HTTP tools use GET and retain metadata and a bounded body hash, not the body.
- Cookie values and other unsafe headers are excluded.
- TLS evidence stores certificate metadata and SHA256, not raw certificate bytes.
- The request budget is four: root metadata, one TLS connection, robots.txt, and security.txt.
- Any malformed, repeated, mutated, out-of-scope, or over-budget proposal is denied and recorded.
- The report is evidence-only and explicitly avoids vulnerability claims.

## Operator demo

Install the project dependencies, ensure Ollama is running locally, and pull a model that advertises
the `tools` capability. Then run:

```bash
./scripts/run-sprint14-agentic-mailhost-demo.sh \
  --target https://owned.example/ \
  --program owned-program \
  --target-alias owned-mail \
  --authorization-reference owner-approved-sprint14 \
  --operator-approved \
  --model gemma4:latest
```

The target must be owned or otherwise explicitly authorized. Private output is written under
`.aotp/campaigns/<program>/<run-id>/`. Review `state/campaign-result.json`, the three hashed
evidence files, and `reports/due-diligence.md`.

## Acceptance proof commands

```bash
python3 -m compileall -q src tests scripts
python3 -m pytest \
  tests/test_agent_workspace.py \
  tests/test_model_proposals.py \
  tests/test_model_proposal_gate.py \
  tests/test_agent_tools_metadata.py \
  tests/test_deep_agent_bootstrap.py \
  tests/test_agentic_campaign_loop.py
bash scripts/validate-repository-safety.sh
make check
```

The live demo evidence is private and ignored. The sprint closeout record under
`docs/development-evidence/sprint-14/` contains only sanitized hashes, tool versions, validation
results, and alias-only acceptance facts.
