# Sensitive Evidence Vault

## Two evidence planes

The normal evidence plane stores redacted, hashed artifacts suitable for ordinary analysis and
report packaging. The encrypted sensitive evidence vault stores campaign-scoped proof that cannot
safely enter normal evidence.

Classifications are `public`, `restricted`, `secret`, `poc_sensitive`, `recipient_only`, and
`do_not_store`. Classification controls storage, retention, access, export, and report inclusion.

## Campaign storage and access

The vault may contain discovered passwords, session or CSRF tokens, API and private keys, hashes,
TOTP weakness proof, exploit inputs, raw response excerpts, PoC artifacts, and campaign key
material needed across iterations. Normal evidence refers to these artifacts by opaque vault
handle.

The agent and approved tools may access raw vault content when the active campaign ROE grants
access, campaign context and artifact classification permit it, and the stated purpose is allowed.
Every read records campaign id, artifact handle, purpose, agent or tool identity, decision, and
time. Retention and export rules are enforced independently.

Secret-bearing tool interfaces resolve a vault handle for in-memory use without placing the raw
value in argv, normal logs, normal evidence, or public reports. A classified PoC workspace may use
vault-backed material for authorized analysis, validation, replay, and reproducible proof.

Sensitive annex export and any report inclusion require explicit human approval. The normal report
excludes raw vault material by default and may refer to an approved, separately packaged annex.
