"""Evidence-bound verifier verdict records."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from .redaction import assert_value_redacted


class Verdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    MANUAL_REVIEW = "manual_review"
    STOPPED_BY_POLICY = "stopped_by_policy"


class Confidence(StrEnum):
    NOT_ASSESSED = "not_assessed"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class VerificationResult:
    verdict: str
    confidence: str
    rationale: str
    evidence_manifest_sha256: str
    evidence_references: list[str]
    verifier: str
    verified_at_utc: str
    schema_version: str = "1.0"
    result_sha256: str | None = None

    def validate(self) -> None:
        if self.schema_version != "1.0":
            raise ValueError("unsupported verification schema")
        if self.verdict not in set(Verdict):
            raise ValueError("unsupported verifier verdict")
        if self.confidence not in set(Confidence):
            raise ValueError("unsupported verifier confidence")
        if not self.rationale or not self.verifier:
            raise ValueError("verification rationale and verifier are required")
        if len(self.evidence_manifest_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.evidence_manifest_sha256
        ):
            raise ValueError("verification requires a valid evidence manifest SHA256")
        if self.verdict in {Verdict.PASS, Verdict.FAIL} and not self.evidence_references:
            raise ValueError("pass and fail verdicts require evidence references")
        if len(self.evidence_references) != len(set(self.evidence_references)):
            raise ValueError("verification evidence references must be unique")
        try:
            timestamp = datetime.fromisoformat(self.verified_at_utc.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("verification timestamp is invalid") from exc
        if timestamp.tzinfo is None:
            raise ValueError("verification timestamp must include a timezone")
        assert_value_redacted(asdict(self))
        if self.result_sha256 is not None and self.result_sha256 != verification_digest(self):
            raise ValueError("verification result integrity check failed")


def verification_digest(result: VerificationResult) -> str:
    payload = asdict(result)
    payload["result_sha256"] = None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def create_verification(
    *,
    verdict: str,
    confidence: str,
    rationale: str,
    evidence_manifest_sha256: str,
    evidence_references: list[str],
    verifier: str,
) -> VerificationResult:
    result = VerificationResult(
        verdict=verdict,
        confidence=confidence,
        rationale=rationale,
        evidence_manifest_sha256=evidence_manifest_sha256,
        evidence_references=evidence_references,
        verifier=verifier,
        verified_at_utc=datetime.now(UTC).isoformat(),
    )
    result.validate()
    return result


def write_verification(result: VerificationResult, path: str | Path) -> Path:
    result.result_sha256 = None
    result.validate()
    result.result_sha256 = verification_digest(result)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".verification.", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(asdict(result), handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, output)
        os.chmod(output, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def load_verification(path: str | Path) -> VerificationResult:
    try:
        result = VerificationResult(**json.loads(Path(path).read_text(encoding="utf-8")))
        result.validate()
        return result
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"verification result is invalid: {path}: {exc}") from exc


VERIFICATION_ASSISTANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "evidence_summary": {"type": "string"},
        "evidence_references": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "string"},
    },
    "required": ["evidence_summary", "evidence_references", "uncertainty"],
    "additionalProperties": False,
}

REPORT_ASSISTANCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "draft_summary": {"type": "string"},
        "evidence_references": {"type": "array", "items": {"type": "string"}},
        "caveat": {"type": "string"},
    },
    "required": ["title", "draft_summary", "evidence_references", "caveat"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class VerificationAssistance:
    evidence_summary: str
    evidence_references: tuple[str, ...]
    uncertainty: str


@dataclass(frozen=True)
class ReportAssistance:
    title: str
    draft_summary: str
    evidence_references: tuple[str, ...]
    caveat: str


def prepare_model_evidence_summaries(
    evidence_summaries: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if not evidence_summaries:
        raise ValueError("model assistance requires evidence summaries")
    prepared: list[dict[str, str]] = []
    for index, item in enumerate(evidence_summaries):
        if not isinstance(item, dict) or set(item) != {"evidence_reference", "summary"}:
            raise ValueError(
                f"evidence_summaries[{index}] must contain only evidence_reference and summary"
            )
        reference = item.get("evidence_reference")
        summary = item.get("summary")
        if (
            not isinstance(reference, str)
            or not reference.strip()
            or not isinstance(summary, str)
            or not summary.strip()
        ):
            raise ValueError("model evidence summaries require non-empty text")
        prepared.append(
            {
                "evidence_reference": reference.strip(),
                "summary": summary.strip(),
            }
        )
    references = [item["evidence_reference"] for item in prepared]
    if len(references) != len(set(references)):
        raise ValueError("model evidence summary references must be unique")
    return prepared


def _validated_references(value: Any, allowed: set[str]) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise ValueError("model assistance evidence references must be unique non-empty text")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            "model assistance referenced unknown evidence: " + ", ".join(unknown)
        )
    return tuple(value)


def _required_assistance_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"model assistance {field} must be non-empty text")
    return value.strip()


def parse_verification_assistance(
    result: dict[str, Any],
    allowed_evidence_references: set[str],
) -> VerificationAssistance:
    expected = {"evidence_summary", "evidence_references", "uncertainty"}
    if not isinstance(result, dict) or set(result) != expected:
        raise ValueError(
            "verification assistance cannot set verdict, authorization, confidence, or policy"
        )
    return VerificationAssistance(
        evidence_summary=_required_assistance_text(
            result["evidence_summary"], "evidence_summary"
        ),
        evidence_references=_validated_references(
            result["evidence_references"], allowed_evidence_references
        ),
        uncertainty=_required_assistance_text(result["uncertainty"], "uncertainty"),
    )


def parse_report_assistance(
    result: dict[str, Any],
    allowed_evidence_references: set[str],
) -> ReportAssistance:
    expected = {"title", "draft_summary", "evidence_references", "caveat"}
    if not isinstance(result, dict) or set(result) != expected:
        raise ValueError(
            "report assistance cannot set severity, authorization, impact, or policy"
        )
    return ReportAssistance(
        title=_required_assistance_text(result["title"], "title"),
        draft_summary=_required_assistance_text(
            result["draft_summary"], "draft_summary"
        ),
        evidence_references=_validated_references(
            result["evidence_references"], allowed_evidence_references
        ),
        caveat=_required_assistance_text(result["caveat"], "caveat"),
    )


def request_verification_assistance(
    adapter: Any,
    evidence_summaries: list[dict[str, Any]],
) -> VerificationAssistance:
    prepared = prepare_model_evidence_summaries(evidence_summaries)
    references = {item["evidence_reference"] for item in prepared}
    result = adapter.generate(
        "Summarize only the provided evidence and state uncertainty. Do not set a verdict.",
        {"evidence_summaries": prepared},
        VERIFICATION_ASSISTANCE_SCHEMA,
    )
    return parse_verification_assistance(result, references)


def request_report_assistance(
    adapter: Any,
    evidence_summaries: list[dict[str, Any]],
) -> ReportAssistance:
    prepared = prepare_model_evidence_summaries(evidence_summaries)
    references = {item["evidence_reference"] for item in prepared}
    result = adapter.generate(
        "Draft evidence-only language with an explicit caveat. Do not infer impact or severity.",
        {"evidence_summaries": prepared},
        REPORT_ASSISTANCE_SCHEMA,
    )
    return parse_report_assistance(result, references)
