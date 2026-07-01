# Slice 14.6: Native Metadata Tools

Implemented bounded GET metadata, TLS metadata, robots.txt, and security.txt tools. Redirects are
not followed. HTTP bodies are bounded and hashed, cookie headers are excluded, and TLS evidence
stores certificate metadata and digest rather than raw certificate bytes.

Proof: focused tests verify exact methods and paths, request counts, body and certificate hashing,
header filtering, URL rejection, SNI matching, and no raw certificate persistence.
