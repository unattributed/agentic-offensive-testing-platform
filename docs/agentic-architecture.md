# Agentic Architecture

## Execution environment

AOTP runs locally with Ollama and Parrot-compatible FOSS tooling. A bounded campaign workspace
under `.aotp/campaigns/<program>/<run-id>/` contains private state, evidence, checkpoints, PoC
artifacts, and report outputs. Private operational data remains ignored by git.

## Delegation

A LangChain Deep Agent supervisor decomposes campaign objectives and delegates to purpose-specific
AOTP subagents and skills. Delegates receive only the campaign context and classified evidence
needed for their task. They cannot expand scope or grant themselves authority.

## Steering

The deterministic policy gate evaluates every structured objective and native tool call against
the active campaign, human-defined ROE, scope, risk tier, argument schema, budgets, stop
conditions, artifact classification, and approval record. Human steering can allow, deny, pause,
redirect, or stop work. Denied calls become evidence.

## Context management

The supervisor maintains bounded campaign state, evidence summaries, coverage, decisions, and
checkpoint references. Raw sensitive material stays in encrypted campaign storage and is resolved
only for an authorized agent or secret-bearing tool. Resume and replay recheck current policy.

## Components

The native tool registry exposes typed HTTP, TLS, browser, proxy, scanner, and constrained Parrot
wrappers directly to the Deep Agent without MCP. FOSS adapters execute only approved calls.

Normal artifacts enter the hashed evidence archive. Sensitive artifacts and campaign key material
enter the encrypted vault. A classified PoC workspace may use vault handles to build reproducible
proof. Analysis and finding review require evidence sufficiency. Report packaging produces a
normal report plus an optional, separately approved sensitive annex. Submission remains manual.
