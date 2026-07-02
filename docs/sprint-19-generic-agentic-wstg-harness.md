# Sprint 19: Generic Agentic WSTG Execution Harness

Sprint 19 moves AOTP from a Juice Shop-specific campaign runner toward a reusable WSTG campaign loop.

## Implemented in this slice

- Generic target runtime contract for approved campaign targets.
- Fail-closed handling for planned targets, including crAPI live runtime pending.
- Generic read-only WSTG action planner.
- Generic campaign state model with auditable agent decisions.
- Deterministic campaign evidence writer and SHA256 manifest.
- Proof request model for missing evidence, rather than overclaimed findings.
- Generic live campaign harness that can run against the implemented local Juice Shop runtime.

## Boundary

This slice is intentionally limited to bounded read-only campaign actions. It does not perform authenticated workflows, browser-controlled submissions, intrusive active probing, or exploit validation. Those capabilities are scheduled for later sprints.

## Acceptance

AOTP can run a generic WSTG live campaign against the supported local Juice Shop profile, write normalized evidence, update state, create evidence-bound candidate findings, request missing proof, and keep crAPI registered but not live executable.
