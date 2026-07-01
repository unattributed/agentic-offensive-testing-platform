# Slice 14.1: Ollama Deep Agent Bootstrap

Implemented strict discovery on `http://127.0.0.1`, installed-model and digest verification,
tool-capability validation, CPU-safe local inference, bounded model calls, and LangChain
`ChatOllama` construction.

Proof: bootstrap negative tests reject localhost aliases, remote endpoints, credentials, unsafe
paths, missing models, non-tool models, invalid timeouts, and invalid GPU counts. The accepted live
model digest is recorded only in the sanitized closeout evidence.
