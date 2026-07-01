"""In-memory interfaces for tools that need secret material."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .agent_vault_access import VaultAccessContext, read_vault_material
from .evidence_classifier import assert_normal_evidence_safe
from .roe import RulesOfEngagement
from .sensitive_vault import SensitiveVault
from .vault_handles import VaultHandle


class SecretBearingToolError(ValueError):
    """Raised when a secret-bearing tool attempts to leak raw material."""


@dataclass(frozen=True)
class SecretToolResult:
    tool_name: str
    handle: str
    safe_result: dict[str, Any]
    argv: tuple[str, ...]
    log_lines: tuple[str, ...]


def run_secret_bearing_tool(
    *,
    tool_name: str,
    vault: SensitiveVault,
    handle: VaultHandle | str,
    context: VaultAccessContext,
    roe: RulesOfEngagement,
    argv_template: tuple[str, ...],
    handler: Callable[[bytes], dict[str, Any]],
) -> SecretToolResult:
    """Resolve one handle for a callable without placing the raw value in argv or logs."""

    if any("{secret}" in item or "{raw}" in item for item in argv_template):
        raise SecretBearingToolError("secret-bearing tools cannot place raw material in argv")
    read = read_vault_material(vault, handle, context=context, roe=roe)
    safe_result = handler(read.payload)
    encoded_result = repr(safe_result)
    assert_normal_evidence_safe(encoded_result, context="secret-bearing tool result")
    return SecretToolResult(
        tool_name=tool_name,
        handle=read.handle.uri,
        safe_result=safe_result,
        argv=tuple(argv_template),
        log_lines=(
            f"tool={tool_name}",
            f"handle={read.handle.uri}",
            "raw_material=not_logged",
        ),
    )


def assert_no_secret_in_process_surface(result: SecretToolResult, secret: bytes) -> None:
    marker = secret.decode("utf-8", "ignore")
    surface = "\n".join((*result.argv, *result.log_lines, repr(result.safe_result)))
    if marker and marker in surface:
        raise SecretBearingToolError("secret material appeared in process surface")
