# Ollama local models

The adapter defaults to `http://localhost:11434` and JSON output. Configuration examples cover `qwen3:8b`, `qwen2.5-coder:7b`, `qwen2.5-coder:14b`, `deepseek-r1:8b`, and `qwen3-vl:8b`.

Prompts are sanitized before transport. Secrets, cookies, bearer tokens, private keys, raw credentials, session identifiers, and email addresses are not allowed. Model output is advisory and cannot authorize scope or bypass policy. An unavailable service fails gracefully.

See the official [Ollama structured outputs documentation](https://docs.ollama.com/capabilities/structured-outputs).
