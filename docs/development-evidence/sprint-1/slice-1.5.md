# Slice 1.5 evidence: fail-closed policy coverage

## Functional result

Network cases now require an explicit domain and service. Exact domain matching is the default. A wildcard such as `*.example.invalid` permits a real subdomain but does not silently include the apex. Target aliases, services, APIs, environments, accounts, actions, and categories remain independent policy boundaries.

The new `aotp policy-check` command performs the same complete live preflight as execution without creating state, evidence, or network traffic. Its structured result is suitable for operator review and automation.

## Validation

Command:

```bash
python3 -m pytest
```

Result:

```text
62 passed in 0.20s
```

Coverage includes positive dry-run and live authorization paths plus denial for missing or malformed configuration, missing private profile or approval, placeholder references, mismatched or expired authorization, future policy acceptance, out-of-scope targets, domain expansion, wildcard apex expansion, unlisted services and APIs, unlisted environments, unapproved accounts, forbidden actions and categories, excessive rates, inactive windows, rules-of-engagement mismatch, missing stop conditions, unsafe evidence paths, required confidentiality gaps, absent human approval, redaction failure, and automatic submission.

The policy-check test proves that an allowed preflight leaves no `.aotp` runtime directory.
