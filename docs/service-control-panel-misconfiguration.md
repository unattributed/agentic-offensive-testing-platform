# Service control panel misconfiguration

This module applies only to an explicitly listed panel, dashboard, console, portal, monitoring service, CI/CD interface, or registry.

Safe checks may observe a login page, headers, TLS posture, version leakage, default content, indexing, unauthenticated metadata, and configuration disclosure. Credential attacks, lockout-triggering behavior, destructive administration, and discovery of additional panels are denied.

Standalone cases and campaigns must use matching `module` and `category` values, an explicitly
scoped `panel_alias`, a supported `panel_type`, and a non-empty safe observation list. Scope-level
denials override approvals.

Panel campaigns must declare the `authentication_lockout_risk` stop condition. An explicit
lockout-risk signal pauses before execution and writes zero-request evidence. Human review for
candidate creation is stored in a decision record bound to the evidence manifest SHA256. Reports
re-validate that record and render only fields from the hashed panel evidence artifact.
