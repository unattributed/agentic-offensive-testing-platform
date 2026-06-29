# Repository redaction policy

Committed files must not contain real targets, organization names, program details, accounts, credentials, cookies, tokens, keys, email addresses, correspondence, findings, customer data, screenshots, proxy captures, or proprietary evidence.

Private profiles, scopes, memory, evidence, reports, traces, and screenshots belong in ignored paths. `scripts/validate-repository-safety.sh` is a coarse defense, not a substitute for review. Before every push, run the validator and inspect `git diff --cached`.
