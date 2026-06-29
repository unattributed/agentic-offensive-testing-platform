# Security policy

## Reporting

Do not open a public issue containing a vulnerability, target, authorization record, credential, cookie, token, private key, private correspondence, customer data, screenshot, or assessment evidence. Use a private repository security advisory or another owner-approved private channel.

## Supported state

The `main` branch is the supported development line. Version 0.1 is a foundational, network-silent harness. Live adapter stubs are not production testing tools.

## Safety invariants

- Private scope and program profiles remain untracked.
- The policy gate is called before every executor.
- Scope is authoritative and cannot be expanded by model output.
- Evidence is alias-based, redacted, and local by default.
- Report submission requires human action outside AOTP.
- Dependencies and external adapter code require license review.

If any invariant fails, stop the campaign and preserve only redacted evidence needed for review.
