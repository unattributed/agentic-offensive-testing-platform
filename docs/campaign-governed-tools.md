# Campaign-Governed Tools

AOTP allows real tool execution only inside an active, authorized campaign. The Deep Agent calls
typed native wrappers; it does not receive an ungoverned shell or direct offensive-tool access.

Each registry entry declares its argument schema, capabilities, risk tier, required ROE grants,
scope rules, budgets, evidence classifications, stop conditions, and approval policy. Proposed
arguments are normalized and checked before any side effect.

Risk tiers range from passive metadata observation through authenticated testing and controlled
exploitation validation. Higher-risk tiers require explicit ROE and/or case-specific human
approval. Denied calls produce evidence with the proposal, policy reason, and campaign identity,
without executing the tool.

Native wrappers govern FOSS adapters and Parrot tools such as curl, openssl, nmap, OWASP ZAP,
Playwright, and mitmproxy. A constrained campaign shell may dispatch an allowlisted command and
argument form only; arbitrary commands, target expansion, and budget bypass are denied.

Tool output is classified, sanitized where appropriate, hashed, and captured as normal evidence or
encrypted sensitive evidence. The agent receives only the evidence view authorized by ROE and
classification.
