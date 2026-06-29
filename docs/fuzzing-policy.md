# Bounded fuzzing policy

Fuzzing requires explicit private authorization plus payload, request, endpoint, response-size, runtime, and retry limits. Safe payload classes and stop conditions must be named.

High-volume, destructive, authentication-abuse, payment, KYC, support, recovery, and state-changing fuzzing are denied unless the exact workflow is expressly authorized. Lockout risk, instability, budget exhaustion, or ambiguity pauses or stops the campaign.
