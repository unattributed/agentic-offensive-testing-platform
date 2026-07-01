# Sprint 15: Campaign-Governed Native Tool Registry

## Result

Sprint 15 adds a fail-closed native tool registry for agentic campaign execution. The agent can ask
for a tool by name, but AOTP resolves that request only through registered typed tool specs, a
human-defined rules-of-engagement object, documented risk tiers, and a mutable request budget. Tool
availability is inventoried separately and never grants authority.

## Delivered slices

| Slice | Delivered evidence |
|---|---|
| 15.1 | `tool_registry.py` maps requests only to registered typed `NativeToolSpec` records |
| 15.2 | `tool_risk_tiers.py` defines ordered tiers from passive metadata through exploitation validation |
| 15.3 | `roe.py` denies tools, hosts, ports, schemes, classifications, or tiers outside human ROE |
| 15.4 | `request_budget.py` denies over-budget calls before execution and does not mutate counters on denial |
| 15.5 | `agent_tools/campaign_shell.py` dispatches only fixed local allowlisted command IDs |
| 15.6 | `agent_tools/nmap_governed.py` builds one fixed single-host, single-port nmap fingerprint command |
| 15.7 | `agent_tools/zap_passive.py` wraps ZAP baseline passive execution with bounded options only |
| 15.8 | `agent_tools/playwright_passive.py` records single-page passive browser metadata without clicks or form submission |
| 15.9 | `tool_registry.py` writes denied calls into campaign evidence with proposal and denial reason |
| 15.10 | `tool_inventory.py` records FOSS tool availability while stating that presence never grants authority |

## Safety boundaries

- No arbitrary shell tool exists. The campaign shell accepts a command identifier, not caller-supplied
  argv.
- Every registry spec declares exact argument names and Python types. Extra or missing arguments deny.
- ROE must name the campaign, target alias, allowed tools, allowed risk tiers, allowed hosts, allowed
  schemes, allowed ports, evidence classifications, and required approval references.
- Service fingerprinting requires an explicit approval reference before the nmap wrapper is allowed.
- Budgets are checked before execution and consumed only after a call is allowed.
- Denied calls are written as campaign evidence and record `executed: false`.
- ZAP passive baseline execution omits active scan options, authentication, hooks, and arbitrary ZAP
  command-line injection.
- Playwright passive metadata collection visits one URL and records metadata counts only.
- FOSS inventory output is informational. It cannot enable a tool, widen scope, or increase budget.

## Tool notes

The nmap wrapper uses a fixed `-Pn -sV --version-light --max-retries 1 --host-timeout 30s -p <port>
-- <host>` command shape for one approved service. The ZAP wrapper uses the baseline script in
passive mode with `-m`, `-I`, and optional JSON or HTML output paths. The Playwright wrapper uses a
single `page.goto` navigation and avoids interaction APIs.

## Acceptance proof commands

```bash
python3 -m compileall -q src tests
python3 -m pytest \
  tests/test_tool_registry.py \
  tests/test_tool_risk_tiers.py \
  tests/test_request_budget.py \
  tests/test_campaign_shell.py \
  tests/test_nmap_governed.py \
  tests/test_zap_passive.py \
  tests/test_playwright_passive.py \
  tests/test_tool_inventory.py
./scripts/validate-repository-safety.sh
make check
```

## Commit suggestion

`implement campaign governed native tool registry`
