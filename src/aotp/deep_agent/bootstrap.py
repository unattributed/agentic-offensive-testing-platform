"""Strict local Ollama discovery and LangChain model bootstrap."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlsplit

from langchain_ollama import ChatOllama


MAX_TAG_RESPONSE_BYTES = 1_048_576


class OllamaBootstrapError(RuntimeError):
    """Raised when local model discovery or validation fails closed."""


@dataclass(frozen=True)
class OllamaRuntimeStatus:
    base_url: str
    model: str
    model_digest: str
    capabilities: tuple[str, ...]
    available: bool


@dataclass(frozen=True)
class OllamaBootstrap:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "gemma4:latest"
    timeout_seconds: int = 10
    num_gpu: int = 0
    opener: Callable[..., Any] = urllib.request.urlopen

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise OllamaBootstrapError(
                "Sprint 14 Ollama endpoint must be unauthenticated HTTP on 127.0.0.1"
            )
        if not isinstance(self.model, str) or not self.model.strip():
            raise OllamaBootstrapError("configured local model must be non-empty")
        if (
            not isinstance(self.timeout_seconds, int)
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds <= 0
            or self.timeout_seconds > 30
        ):
            raise OllamaBootstrapError("Ollama timeout must be between 1 and 30 seconds")
        if (
            not isinstance(self.num_gpu, int)
            or isinstance(self.num_gpu, bool)
            or self.num_gpu < 0
        ):
            raise OllamaBootstrapError("Ollama GPU count must be a non-negative integer")

    def validate(self) -> OllamaRuntimeStatus:
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/api/tags",
            method="GET",
            headers={"Accept": "application/json"},
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read(MAX_TAG_RESPONSE_BYTES + 1)
        except (OSError, TimeoutError, urllib.error.URLError) as exc:
            raise OllamaBootstrapError(
                "local Ollama service is unavailable on 127.0.0.1"
            ) from exc
        if len(raw) > MAX_TAG_RESPONSE_BYTES:
            raise OllamaBootstrapError("Ollama model inventory exceeds the response limit")
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaBootstrapError("Ollama model inventory is invalid JSON") from exc
        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise OllamaBootstrapError("Ollama model inventory is malformed")
        selected = next(
            (
                item
                for item in models
                if isinstance(item, dict)
                and self.model in {item.get("name"), item.get("model")}
            ),
            None,
        )
        if selected is None:
            raise OllamaBootstrapError(
                f"configured local model is not installed: {self.model}"
            )
        capabilities = selected.get("capabilities", [])
        if not isinstance(capabilities, list) or any(
            not isinstance(item, str) for item in capabilities
        ):
            raise OllamaBootstrapError("Ollama model capabilities are malformed")
        if "tools" not in capabilities:
            raise OllamaBootstrapError(
                "configured local model does not advertise tool-calling support"
            )
        digest = selected.get("digest")
        if not isinstance(digest, str) or len(digest) != 64:
            raise OllamaBootstrapError("configured local model digest is missing")
        return OllamaRuntimeStatus(
            base_url=self.base_url.rstrip("/"),
            model=self.model,
            model_digest=digest,
            capabilities=tuple(sorted(capabilities)),
            available=True,
        )

    def build_model(self) -> ChatOllama:
        self.validate()
        return ChatOllama(
            model=self.model,
            base_url=self.base_url.rstrip("/"),
            temperature=0,
            validate_model_on_init=True,
            num_ctx=16_384,
            num_gpu=self.num_gpu,
            num_predict=768,
            client_kwargs={"timeout": 300.0},
        )
