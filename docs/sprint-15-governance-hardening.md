# Sprint 15 Governance Hardening Follow-up

Sprint 15 introduced the campaign-governed native tool registry. The senior review accepted the
architecture as valuable but identified hardening that must land before Sprint 16 builds sensitive
evidence handling on top of the tool plane.

## Hardening requirements

1. Nmap target validation must reject Nmap range expressions, not just shell metacharacters.
2. Request budget must be consumed before a governed executor starts, because failed launched
   traffic still counts against campaign authority.
3. The active agentic campaign loop must use the registry by default, instead of bypassing Sprint
   15 governance through direct function dispatch.
4. Successful registry-mediated tool calls must create evidence records just as denied calls do.
5. Browser and passive scanner tools must have regression tests for out-of-origin navigation or
   crawl output.

## Implemented controls

- `nmap_governed.validate_single_host` rejects CIDR, wildcard, comma-separated, and numeric
  octet-range target expressions. Exact IP addresses and alphabetic DNS hostnames remain allowed.
- `NativeToolRegistry.execute` consumes the approved request budget before invoking the executor.
- `NativeToolRegistry.execute` writes `executed-<tool>-*.json` evidence when a workspace is supplied.
- `run_agentic_campaign` routes default native execution through `NativeToolRegistry`,
  `RulesOfEngagement`, and `RequestBudget`.
- Playwright passive metadata validates that `final_url` remains same-origin.
- ZAP passive baseline validates reported URLs in stdout and stderr before accepting evidence.

## Validation expectation

Local validation must include focused Sprint 15 hardening tests, full `make check`, repository
safety validation, git diff evidence, and a sha256-hashed evidence archive.
