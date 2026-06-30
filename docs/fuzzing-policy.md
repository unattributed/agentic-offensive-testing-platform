# Bounded fuzzing policy

Fuzzing requires explicit private authorization plus payload, request, endpoint, response-size, runtime, and retry limits. Safe payload classes and stop conditions must be named.

High-volume, destructive, authentication-abuse, payment, KYC, support, recovery, and state-changing fuzzing are denied unless the exact workflow is expressly authorized. Lockout risk, instability, budget exhaustion, or ambiguity pauses or stops the campaign.

Dry-run objectives contain payload classes and counts, endpoint request budgets, response-size,
retry, and runtime ceilings, and an optional private corpus reference. They never contain corpus
payload values. Campaigns must persist request and endpoint counters and stop before execution
when any configured safety signal is present.
