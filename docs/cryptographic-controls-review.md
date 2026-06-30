# Cryptographic controls review

Scoped review may cover observable TLS and certificate metadata, cookie transport attributes, provided JWT or token configuration, cryptographic dependency exposure, algorithm indicators, and key-management configuration artifacts.

The policy gate requires the complete metadata schema before execution. It rejects missing TLS,
cookie, token, weak-indicator, or key-management evidence; unsafe paths; raw cookie or token
values; private key material; extraction; brute force; decryption; replay; destructive actions; and
live probing.

Evidence records TLS and certificate metadata, cookie attributes without values, token validation
configuration, weak indicators, and key-management metadata. Review is local and network-silent.
A weak indicator remains an observation until verified evidence and human review support a
finding.
