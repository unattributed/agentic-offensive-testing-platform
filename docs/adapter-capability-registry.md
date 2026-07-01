# Adapter capability registry

Every deferred adapter contract declares:

- supported placeholder or external-reference capabilities;
- private scope, policy, and adapter-specific approval requirements;
- required scope field names without target values;
- evidence handling and provenance requirements;
- denied actions;
- a network-silent default, zero request budget, and disabled live execution; and
- the official or source-project reference used to define the boundary.

The registry is descriptive and does not grant authority. The policy gate still evaluates every
objective. Capability changes require tests, license review, and human review.

The placeholder examples under `examples/adapters/` contain aliases only. Their strict parser
requires `execute: false`, a zero request budget, the contract default mode, supported
capabilities, and complete requirement declarations. Parsed plans are always marked
`placeholder_not_executable`.
