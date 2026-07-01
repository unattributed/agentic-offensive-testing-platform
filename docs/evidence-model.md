# Evidence model

Each manifest records run and campaign iteration identity, UTC time, operator and sponsor aliases, target alias and category, authorization, rules-of-engagement and confidentiality references, case and mappings, adapter, execution mode, policy decision, request count, response metadata, artifact placeholders, hashes, verdict, confidence, candidate reference, inclusion status, and redaction status.

Manifests are atomic, mode `0600`, and protected by a canonical content SHA256. Registered artifacts record role, media type, size, raw and redacted paths and hashes. Verification rejects mutation, missing files, path escape, and symlinks.

Raw target values and secrets are excluded from normal evidence and public report packages.
Structured redaction reports field paths, secret classes and value digests without exposing
values. Sensitive proof material and campaign key material may instead be stored in encrypted,
campaign-scoped vault storage. The agent and approved tools may access raw vault contents only
when the active campaign ROE, context, and artifact classification authorize access. Access is
logged, retention and export rules are enforced, and report inclusion requires a separate
decision. Artifact hashes prove identity, not truth or security impact. A separate verifier result
determines whether evidence supports a candidate.
