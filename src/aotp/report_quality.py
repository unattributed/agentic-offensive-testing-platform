"""Human-reviewed report quality scoring."""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass
class ReportQuality:
    scope_proof: int = 0
    clear_impact: int = 0
    reproducibility: int = 0
    evidence_quality: int = 0
    affected_asset_clarity: int = 0
    risk_explanation: int = 0
    remediation_usefulness: int = 0
    policy_compliance: int = 0
    redaction_status: int = 0
    human_review_completed: int = 0

    def score(self) -> int:
        values = [getattr(self, item.name) for item in fields(self)]
        if any(not isinstance(value, int) or not 0 <= value <= 10 for value in values):
            raise ValueError("quality fields must be integers from 0 through 10")
        return sum(values)
