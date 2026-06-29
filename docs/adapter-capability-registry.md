# Adapter capability registry

Every adapter declares:

- `supports`: bounded operations it can implement;
- `requires`: policy, scope, runtime, or evidence prerequisites; and
- `denies`: operations it will not perform.

The registry is descriptive and does not grant authority. The policy gate still evaluates every objective. Capability changes require tests, license review, and human review.
