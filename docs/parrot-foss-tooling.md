# Parrot and FOSS Tooling

Parrot OS is a supported local FOSS operator platform for AOTP. Supported tool families include
OWASP ZAP, Playwright, nmap, mitmproxy, curl, openssl, jq, and Python.

No paid tool or cloud service is required. AOTP discovers local availability and version metadata,
then maps each tool to a typed native wrapper, risk tier, capability set, scope rule, budget,
approval policy, and evidence classification. Discovery never grants execution authority.

Missing tools produce an availability result rather than an unsafe fallback. Installed tools still
run only when the active campaign ROE and policy gate allow the exact invocation.
