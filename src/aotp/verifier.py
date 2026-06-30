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
