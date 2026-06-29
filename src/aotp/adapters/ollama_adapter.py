"""Local Ollama structured JSON adapter."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..redaction import assert_redacted, sanitize_for_model


@dataclass(frozen=True)
class OllamaAdapter:
    model: str = "qwen3:8b"
    base_url: str = "http://localhost:11434"

    supports = ("structured_planning", "evidence_summarization", "classification", "draft_language")
    requires = ("localhost_or_approved_endpoint", "redacted_input")
    denies = ("scope_authorization", "policy_override", "raw_secrets")

    def build_prompt(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        cleaned = sanitize_for_model({"task": task, "payload": payload})
        encoded = json.dumps(cleaned, sort_keys=True)
        assert_redacted(encoded)
        return {
            "model": self.model,
            "format": "json",
            "stream": False,
            "prompt": encoded,
        }

    def generate(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(self.build_prompt(task, payload)).encode()
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read())
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("local Ollama service is unavailable or returned invalid JSON") from exc
        return result
