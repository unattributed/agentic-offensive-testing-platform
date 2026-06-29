# Campaign loop

Each bounded iteration:

1. reads the private scope and rules of engagement;
2. selects the next approved objective;
3. applies policy;
4. executes a deterministic adapter or records denial;
5. writes redacted evidence;
6. records a verifier verdict;
7. checkpoints campaign state;
8. updates evidence-bound candidates;
9. continues, pauses, or stops; and
10. makes evidence available to reporting.

Iteration, runtime, request, endpoint, and payload budgets are hard limits. Model suggestions never become authorization.
