"""Privacy-preserving aggregate operator metrics."""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .redaction import assert_value_redacted

SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class OperatorMetrics:
    measurement_period_start_utc: str
    measurement_period_end_utc: str
    manual_hours_spent: float = 0
    agent_assisted_hours_spent: float = 0
    number_of_requests: int = 0
    number_of_cases_executed: int = 0
    number_of_candidates_generated: int = 0
    number_confirmed: int = 0
    number_submitted: int = 0
    number_accepted: int = 0
    number_rejected: int = 0
    number_duplicate: int = 0
    bounty_amount: float = 0
    estimated_tool_cost: float = 0
    currency_code: str = "USD"
    schema_version: str = SCHEMA_VERSION
    data_classification: str = "private_aggregate"

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported operator metrics schema")
        if self.data_classification != "private_aggregate":
            raise ValueError("operator metrics must be private aggregate data")
        start = _parse_timestamp(
            self.measurement_period_start_utc, "measurement_period_start_utc"
        )
        end = _parse_timestamp(
            self.measurement_period_end_utc, "measurement_period_end_utc"
        )
        if start >= end:
            raise ValueError("measurement period must have positive duration")
        for field in ("manual_hours_spent", "agent_assisted_hours_spent"):
            _non_negative_number(getattr(self, field), field)
        count_fields = (
            "number_of_requests",
            "number_of_cases_executed",
            "number_of_candidates_generated",
            "number_confirmed",
            "number_submitted",
            "number_accepted",
            "number_rejected",
            "number_duplicate",
        )
        for field in count_fields:
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")
        _non_negative_number(self.bounty_amount, "bounty_amount")
        _non_negative_number(self.estimated_tool_cost, "estimated_tool_cost")
        if (
            not isinstance(self.currency_code, str)
            or len(self.currency_code) != 3
            or not self.currency_code.isascii()
            or not self.currency_code.isalpha()
            or not self.currency_code.isupper()
        ):
            raise ValueError("currency_code must be a three-letter uppercase code")
        if self.number_confirmed > self.number_of_candidates_generated:
            raise ValueError("confirmed count cannot exceed candidate count")
        if self.number_submitted > self.number_confirmed:
            raise ValueError("submitted count cannot exceed confirmed count")
        resolved = (
            self.number_accepted + self.number_rejected + self.number_duplicate
        )
        if resolved > self.number_submitted:
            raise ValueError("resolved outcomes cannot exceed submitted count")
        assert_value_redacted(asdict(self))


def _parse_timestamp(value: Any, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} is invalid") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _non_negative_number(value: Any, field: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{field} must be a finite non-negative number")


def write_operator_metrics(metrics: OperatorMetrics, path: str | Path) -> Path:
    metrics.validate()
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".operator-metrics.", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(metrics), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_operator_metrics(path: str | Path) -> OperatorMetrics:
    try:
        data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("metrics root must be a mapping")
        metrics = OperatorMetrics(**data)
        metrics.validate()
        return metrics
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"operator metrics are invalid: {path}: {exc}") from exc
