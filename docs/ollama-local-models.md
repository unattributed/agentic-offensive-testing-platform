# Ollama local models

The adapter defaults to `http://localhost:11434`. Configuration requires an unauthenticated
loopback HTTP endpoint, an allowlisted model, structured JSON, recursive redaction, remote
endpoints disabled, and a timeout of at most 30 seconds. Configuration examples cover `qwen3:8b`,
`qwen2.5-coder:7b`, `qwen2.5-coder:14b`, `deepseek-r1:8b`, and `qwen3-vl:8b`.

Requests are non-streaming and pass a JSON schema in the `format` field. Temperature is zero,
prompt size and response size are bounded, and the nested response is parsed with strict finite
JSON and independently validated against the schema.

Prompts are sanitized before transport. Secrets, cookies, bearer tokens, private keys, raw
credentials, session identifiers, tokens, access keys, passwords, and email addresses are not
allowed in the serialized body. Unsafe prompt values fail before transport. Secret-bearing model
output is rejected.

The v0.1 planner can select only an objective ID already approved by deterministic campaign state.
Sprint 14 extends the local model through a LangChain Deep Agent that emits structured objectives
and native tool-call proposals. The deterministic AOTP policy gate still decides execution.
Verification and report assistance receives only evidence views allowed by campaign ROE and
classification, and can cite only supplied evidence references. It cannot set authorization,
policy, verdict, confidence, severity, or impact. An unavailable local service fails with a
bounded error.

Sensitive vault material is not included in ordinary prompts. A later authorized campaign flow
may provide the minimum raw material needed for an approved analysis or secret-bearing tool
operation only under the vault access policy, with purpose-bound logging and output controls.

See the official [Ollama structured outputs documentation](https://docs.ollama.com/capabilities/structured-outputs).
