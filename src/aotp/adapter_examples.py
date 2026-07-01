"""Strict parser for inert adapter integration examples."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .capability_registry import get_adapter, list_adapters
from .config import (
    ConfigError,
    load_yaml,
    require_bool,
    require_list,
    require_mapping,
    require_non_negative_int,
    require_text,
    require_text_list,
)

SAFE_ALIAS = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


@dataclass(frozen=True)
class PlaceholderIntegrationPlan:
    example_id: str
    adapter_id: str
    execution_mode: str
    requested_capabilities: tuple[str, ...]
    required_approvals: tuple[str, ...]
    scope_field_aliases: dict[str, str]
    evidence_handling: tuple[str, ...]
    provenance_aliases: dict[str, str]
    plan_status: str = "placeholder_not_executable"
    network_silent: bool = True
    live_execution_enabled: bool = False
    request_budget: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _reject_unknown(mapping: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ConfigError(f"{field} contains unknown fields: {', '.join(unknown)}")


def _safe_alias_mapping(value: Any, field: str) -> dict[str, str]:
    mapping = require_mapping(value, field)
    result: dict[str, str] = {}
    for key, raw_value in mapping.items():
        name = require_text(key, f"{field} key")
        alias = require_text(raw_value, f"{field}.{name}")
        if SAFE_ALIAS.fullmatch(alias) is None:
            raise ConfigError(f"{field}.{name} must be a safe placeholder alias")
        result[name] = alias
    return result


def parse_placeholder_examples(data: dict[str, Any]) -> tuple[PlaceholderIntegrationPlan, ...]:
    _reject_unknown(data, {"schema_version", "examples"}, "adapter examples")
    if require_text(data.get("schema_version"), "schema_version") != "1.0":
        raise ConfigError("unsupported adapter example schema_version")
    raw_examples = require_list(data.get("examples"), "examples")
    plans: list[PlaceholderIntegrationPlan] = []
    for index, raw_example in enumerate(raw_examples):
        field = f"examples[{index}]"
        example = require_mapping(raw_example, field)
        _reject_unknown(
            example,
            {
                "example_id",
                "adapter_id",
                "execution_mode",
                "execute",
                "request_budget",
                "requested_capabilities",
                "approval_requirements",
                "scope_field_aliases",
                "evidence_handling",
                "provenance_aliases",
            },
            field,
        )
        adapter_id = require_text(example.get("adapter_id"), f"{field}.adapter_id")
        try:
            contract = get_adapter(adapter_id)
        except KeyError as exc:
            raise ConfigError(str(exc)) from exc
        if require_bool(example.get("execute"), f"{field}.execute") is not False:
            raise ConfigError(f"{field}.execute must remain false")
        request_budget = require_non_negative_int(
            example.get("request_budget"), f"{field}.request_budget"
        )
        if request_budget != 0:
            raise ConfigError(f"{field}.request_budget must remain zero")
        execution_mode = require_text(
            example.get("execution_mode"), f"{field}.execution_mode"
        )
        if execution_mode != contract["default_execution_mode"]:
            raise ConfigError(f"{field}.execution_mode must match the adapter default")
        capabilities = require_text_list(
            example.get("requested_capabilities"),
            f"{field}.requested_capabilities",
            allow_empty=False,
        )
        if len(capabilities) != len(set(capabilities)):
            raise ConfigError(f"{field}.requested_capabilities must be unique")
        unsupported = sorted(set(capabilities) - set(contract["supported_capabilities"]))
        if unsupported:
            raise ConfigError(
                f"{field} requests unsupported capabilities: {', '.join(unsupported)}"
            )
        approvals = require_text_list(
            example.get("approval_requirements"),
            f"{field}.approval_requirements",
            allow_empty=False,
        )
        if len(approvals) != len(set(approvals)):
            raise ConfigError(f"{field}.approval_requirements must be unique")
        if set(approvals) != set(contract["required_approvals"]):
            raise ConfigError(f"{field}.approval_requirements must declare every requirement")
        scope_aliases = _safe_alias_mapping(
            example.get("scope_field_aliases"),
            f"{field}.scope_field_aliases",
        )
        if set(scope_aliases) != set(contract["required_scope_fields"]):
            raise ConfigError(f"{field}.scope_field_aliases must cover required scope fields")
        evidence_handling = require_text_list(
            example.get("evidence_handling"),
            f"{field}.evidence_handling",
            allow_empty=False,
        )
        if len(evidence_handling) != len(set(evidence_handling)):
            raise ConfigError(f"{field}.evidence_handling must be unique")
        if set(evidence_handling) != set(contract["required_evidence_handling"]):
            raise ConfigError(f"{field}.evidence_handling must declare every requirement")
        provenance_aliases = _safe_alias_mapping(
            example.get("provenance_aliases"),
            f"{field}.provenance_aliases",
        )
        if set(provenance_aliases) != set(contract["provenance_requirements"]):
            raise ConfigError(f"{field}.provenance_aliases must cover provenance requirements")
        example_id = require_text(example.get("example_id"), f"{field}.example_id")
        if SAFE_ALIAS.fullmatch(example_id) is None:
            raise ConfigError(f"{field}.example_id must be a safe placeholder alias")
        plans.append(
            PlaceholderIntegrationPlan(
                example_id=example_id,
                adapter_id=adapter_id,
                execution_mode=execution_mode,
                requested_capabilities=tuple(capabilities),
                required_approvals=tuple(approvals),
                scope_field_aliases=scope_aliases,
                evidence_handling=tuple(evidence_handling),
                provenance_aliases=provenance_aliases,
            )
        )
    example_ids = [plan.example_id for plan in plans]
    adapter_ids = [plan.adapter_id for plan in plans]
    if len(example_ids) != len(set(example_ids)):
        raise ConfigError("adapter example IDs must be unique")
    expected_adapters = {adapter["adapter_id"] for adapter in list_adapters()}
    if set(adapter_ids) != expected_adapters or len(adapter_ids) != len(expected_adapters):
        raise ConfigError("adapter examples must include each adapter exactly once")
    return tuple(plans)


def load_placeholder_examples(path: str | Path) -> tuple[PlaceholderIntegrationPlan, ...]:
    return parse_placeholder_examples(load_yaml(path).data)
