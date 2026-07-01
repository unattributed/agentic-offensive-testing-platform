# Post-Sprint 13 Direction

The settled AOTP direction is a local-first, FOSS-first, authorized-only, evidence-first, and
campaign-governed offensive testing platform.

## Architecture decision

AOTP uses a local Ollama model with a LangChain Deep Agent supervisor. The supervisor delegates to
AOTP subagents and skills, and calls AOTP-native tools directly. MCP is not part of the core
architecture and no MCP dependency belongs in the current roadmap.

```text
Ollama local model
  -> LangChain Deep Agent supervisor
  -> AOTP subagents and skills
  -> AOTP campaign-governed native tool registry
  -> AOTP policy gate and human approval steering
  -> FOSS adapters and Parrot tools
  -> evidence archive, sensitive vault, analysis, PoC, report package
```

The workflow model consists of execution environment, delegation, steering, and context
management. Models propose and reason; the deterministic control plane validates campaign context,
scope, ROE, tool risk, arguments, budgets, evidence rules, and approval before execution.

## Operator uses

AOTP supports authorized blackbox, graybox, and clearbox campaigns for HackerOne and Bugcrowd
operators, internal security teams, enterprise AppSec teams, red teams, and financial services
security teams working under an accepted program policy, internal ROE, or authorized SOW.

Parrot OS is a supported local operator environment. The platform uses governed FOSS tools and
does not require a paid tool or cloud service. Submission and disclosure are manual-only.

## Sensitive material

Encrypted campaign storage may hold sensitive proof and campaign key material. The agent and
approved tools may access raw vault contents only when the campaign ROE authorizes access, the
campaign context is active, the classification permits access, and all access, retention, export,
and report-inclusion controls are enforced.

Normal evidence and public report packages must not accidentally contain raw vault material.

## Current implementation checkpoint

As of main commit `ba1c484dc6a5cbc967a229059003c1472dde9499`, the post-Sprint 13 direction has advanced through Sprint 17 and its follow-up. The current implementation includes the local Deep Agent runtime, campaign-governed native tool registry, sensitive evidence vault, WSTG campaign coverage engine, and the WSTG execution adapter contract. The adapter contract preserves OSMAP-style testing discipline while remaining network-silent by itself; live authenticated workflows remain governed by later sprint scope, ROE, approvals, budgets, redaction, and evidence controls.
