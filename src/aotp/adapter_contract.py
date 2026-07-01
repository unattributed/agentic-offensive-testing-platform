"""Strict network-silent contracts for deferred live adapter integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


@dataclass(frozen=True)
class AdapterContract:
    adapter_id: str
    display_name: str
    source_reference: str
    supported_capabilities: tuple[str, ...]
    required_approvals: tuple[str, ...]
    required_scope_fields: tuple[str, ...]
    required_evidence_handling: tuple[str, ...]
    denied_actions: tuple[str, ...]
    default_execution_mode: str
    live_readiness_status: str
    optional_dependency_status: str
    provenance_requirements: tuple[str, ...]
    network_silent_default: bool = True
    live_execution_enabled: bool = False
    default_request_budget: int = 0

    def __post_init__(self) -> None:
        text_fields = {
            "adapter_id": self.adapter_id,
            "display_name": self.display_name,
            "source_reference": self.source_reference,
            "default_execution_mode": self.default_execution_mode,
            "live_readiness_status": self.live_readiness_status,
            "optional_dependency_status": self.optional_dependency_status,
        }
        if any(not isinstance(value, str) or not value.strip() for value in text_fields.values()):
            raise ValueError("adapter contract text fields must be non-empty")
        parsed_source = urlsplit(self.source_reference)
        if parsed_source.scheme != "https" or not parsed_source.hostname:
            raise ValueError("adapter contract source_reference must be an HTTPS URL")
        tuple_fields = {
            "supported_capabilities": self.supported_capabilities,
            "required_approvals": self.required_approvals,
            "required_scope_fields": self.required_scope_fields,
            "required_evidence_handling": self.required_evidence_handling,
            "denied_actions": self.denied_actions,
            "provenance_requirements": self.provenance_requirements,
        }
        for field, values in tuple_fields.items():
            if (
                not isinstance(values, tuple)
                or not values
                or any(not isinstance(value, str) or not value.strip() for value in values)
                or len(values) != len(set(values))
            ):
                raise ValueError(f"adapter contract {field} must contain unique non-empty text")
        if self.default_execution_mode not in {"dry_run", "external_reference_only"}:
            raise ValueError("adapter contract default execution mode is unsafe")
        if self.live_readiness_status not in {"deferred", "external_reference_only"}:
            raise ValueError("adapter contract live readiness status is invalid")
        if self.optional_dependency_status not in {
            "not_a_dependency",
            "optional_not_required",
        }:
            raise ValueError("adapter contract optional dependency status is invalid")
        if self.network_silent_default is not True:
            raise ValueError("adapter contracts must default to network silent")
        if self.live_execution_enabled is not False:
            raise ValueError("live adapter execution must remain disabled")
        if self.default_request_budget != 0:
            raise ValueError("adapter contracts must default to a zero request budget")
        if not {
            "explicit_private_scope",
            "policy_gate_approval",
        }.issubset(self.required_approvals):
            raise ValueError("adapter contracts require private scope and policy approval")

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "display_name": self.display_name,
            "source_reference": self.source_reference,
            "supported_capabilities": list(self.supported_capabilities),
            "required_approvals": list(self.required_approvals),
            "required_scope_fields": list(self.required_scope_fields),
            "required_evidence_handling": list(self.required_evidence_handling),
            "denied_actions": list(self.denied_actions),
            "default_execution_mode": self.default_execution_mode,
            "live_readiness_status": self.live_readiness_status,
            "optional_dependency_status": self.optional_dependency_status,
            "network_silent_default": self.network_silent_default,
            "live_execution_enabled": self.live_execution_enabled,
            "default_request_budget": self.default_request_budget,
            "provenance_requirements": list(self.provenance_requirements),
        }
