# Contributing

Contributions are private and require repository-owner authorization. By contributing, you confirm that the work is original or that its provenance and license are documented for proprietary use.

## Change process

1. Keep changes small and map them to a development-plan slice.
2. Add negative tests for every authorization or policy boundary.
3. Use aliases and reserved placeholder domains only.
4. Never commit real profiles, scopes, targets, accounts, secrets, correspondence, evidence, screenshots, findings, or campaign memory.
5. Record any dependency and its license in `docs/dependency-license-inventory.md`.
6. Run `make check`.
7. Have a human review changes that affect live execution, redaction, policy decisions, evidence handling, or reporting.

Do not vendor code from OSMAP, `ai-browser-security-test-suite`, or another project without explicit provenance and licensing review. Prefer clean-room adapter contracts.
