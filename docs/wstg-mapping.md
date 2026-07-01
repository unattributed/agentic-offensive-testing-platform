# WSTG mapping

AOTP uses the [OWASP Web Security Testing Guide](https://owasp.org/www-project-web-security-testing-guide/) for methodology and terminology. Production case definitions should use versioned WSTG identifiers and links because unversioned identifiers may change.

Mappings express coverage intent, not proof that a test ran or passed. Execution evidence and verifier verdicts remain separate.

## Post-Sprint 17 model

The Sprint 17 WSTG campaign coverage engine uses version-qualified identifiers such as
`WSTG-v42-INFO-02` in strategy-map entries, generated objectives, coverage records, and reports.
Coverage dispositions are `tested`, `skipped`, `denied`, `blocked`, and `deferred`.

The Sprint 17 follow-up execution adapter contract adds OSMAP-style execution result statuses:
`pass`, `fail`, `warning`, `skip`, and `not_applicable`. Those statuses are separate from
coverage dispositions. Adapter results update coverage only through the converter in
`src/aotp/wstg/execution_adapter.py`, and finding candidates require failed, redacted,
evidence-backed results.
