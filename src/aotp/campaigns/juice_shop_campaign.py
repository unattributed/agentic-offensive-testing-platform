"""Local OWASP Juice Shop agentic campaign runner.

This runner is intentionally bounded. It uses the local Juice Shop benchmark as a
known-vulnerable target, but it does not embed challenge solutions or destructive
payloads. It resets/validates the benchmark outside this Python module through
scripts, then performs an evidence-producing passive and safe-active campaign
against the loopback-only target.
"""

from __future__ import annotations

import argparse
import hashlib
import html.parser
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from aotp.benchmarks.juice_shop import compare_wstg_observations
from aotp.lab_targets.juice_shop import (
    JUICE_SHOP_AUTHORIZATION_REFERENCE,
    JUICE_SHOP_BASE_URL,
    build_local_juice_shop_wstg_profile,
)
from aotp.wstg import WSTGPlanDisposition, build_wstg_engine_plan

HttpClient = Callable[[str, str, float], "AgenticCampaignObservation"]

_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
}

_DEFAULT_SAFE_PATHS = (
    "/",
    "/robots.txt",
    "/sitemap.xml",
    "/api/Products",
    "/rest/products/search?q=",
)


class JuiceShopCampaignError(ValueError):
    """Raised when the local Juice Shop campaign configuration is unsafe."""


@dataclass(frozen=True)
class LocalJuiceShopCampaignConfig:
    """Configuration for a local-only Juice Shop campaign run."""

    evidence_dir: Path | str
    campaign_id: str = "local-juice-shop-agentic-campaign"
    base_url: str = JUICE_SHOP_BASE_URL
    authorization_reference: str = JUICE_SHOP_AUTHORIZATION_REFERENCE
    request_timeout_seconds: float = 5.0
    max_requests: int = 12
    max_ready_tests: int = 30
    safe_paths: tuple[str, ...] = _DEFAULT_SAFE_PATHS

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlsplit(self.base_url)
        if parsed.scheme != "http":
            raise JuiceShopCampaignError("local Juice Shop campaign must use http")
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise JuiceShopCampaignError("local Juice Shop campaign must stay on loopback")
        if parsed.port != 3000:
            raise JuiceShopCampaignError("local Juice Shop campaign must use port 3000")
        if parsed.username or parsed.password:
            raise JuiceShopCampaignError("base_url credentials are not allowed")
        if parsed.query or parsed.fragment:
            raise JuiceShopCampaignError("base_url query or fragment is not allowed")
        if not self.authorization_reference.strip():
            raise JuiceShopCampaignError("authorization_reference is required")
        if self.request_timeout_seconds <= 0 or self.request_timeout_seconds > 30:
            raise JuiceShopCampaignError("request timeout must be positive and bounded")
        if self.max_requests < 1 or self.max_requests > 50:
            raise JuiceShopCampaignError("max_requests must be between 1 and 50")
        if self.max_ready_tests < 1 or self.max_ready_tests > 97:
            raise JuiceShopCampaignError("max_ready_tests must be between 1 and the catalog size")
        for path in self.safe_paths:
            _validate_safe_path(path)

    @property
    def normalized_base_url(self) -> str:
        return self.base_url if self.base_url.endswith("/") else f"{self.base_url}/"


@dataclass(frozen=True)
class AgenticCampaignDecision:
    """One state-driven decision made during the local campaign."""

    step: int
    action: str
    reason: str
    status: str
    wstg_ids: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgenticCampaignObservation:
    """Redacted HTTP observation captured during the campaign."""

    method: str
    url: str
    status_code: int
    reason: str
    headers: dict[str, str]
    content_type: str
    body_sha256: str
    body_excerpt: str
    body_size_bytes: int
    elapsed_ms: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and self.error is None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgenticCampaignFinding:
    """Evidence-bound candidate or manual-required observation."""

    finding_id: str
    title: str
    status: str
    severity: str
    confidence: str
    wstg_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rationale: str
    next_step: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalJuiceShopCampaignResult:
    """Completed local Juice Shop campaign result."""

    campaign_id: str
    target_alias: str
    base_url: str
    evidence_dir: str
    started_at_utc: str
    completed_at_utc: str
    request_count: int
    observed_wstg_ids: tuple[str, ...]
    decisions: tuple[AgenticCampaignDecision, ...]
    observations: tuple[AgenticCampaignObservation, ...]
    findings: tuple[AgenticCampaignFinding, ...]
    benchmark_comparison: dict[str, Any]
    artifacts: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "evidence_dir": self.evidence_dir,
            "started_at_utc": self.started_at_utc,
            "completed_at_utc": self.completed_at_utc,
            "request_count": self.request_count,
            "observed_wstg_ids": list(self.observed_wstg_ids),
            "decisions": [decision.as_dict() for decision in self.decisions],
            "observations": [observation.as_dict() for observation in self.observations],
            "findings": [finding.as_dict() for finding in self.findings],
            "benchmark_comparison": self.benchmark_comparison,
            "artifacts": self.artifacts,
        }


class _SurfaceParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()
        self.scripts: set[str] = set()
        self.forms: list[dict[str, str]] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "a" and values.get("href"):
            self.links.add(values["href"])
        if tag.lower() == "script" and values.get("src"):
            self.scripts.add(values["src"])
        if tag.lower() == "form":
            self.forms.append({"method": values.get("method", "get").lower(), "action": values.get("action", "")})
        if tag.lower() == "meta":
            key = values.get("name") or values.get("property") or values.get("http-equiv")
            if key:
                self.meta[key.lower()] = values.get("content", "")


@dataclass
class _CampaignWorkspace:
    root: Path
    artifacts: dict[str, str] = field(default_factory=dict)

    def write_json(self, relative: str, payload: Any) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.artifacts[relative] = _sha256_file(path)
        return relative

    def write_text(self, relative: str, payload: str) -> str:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        self.artifacts[relative] = _sha256_file(path)
        return relative


def run_local_juice_shop_agentic_campaign(
    config: LocalJuiceShopCampaignConfig,
    *,
    http_client: HttpClient | None = None,
) -> LocalJuiceShopCampaignResult:
    """Run a bounded local Juice Shop campaign and write normalized evidence.

    The campaign is state-driven: each step records why the next action is safe
    and useful based on prior observations. Only GET requests to same-origin,
    allow-listed paths are performed.
    """

    evidence_dir = Path(config.evidence_dir).expanduser().resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    workspace = _CampaignWorkspace(evidence_dir)
    started = _utc_now()

    profile = build_local_juice_shop_wstg_profile(
        campaign_id=config.campaign_id,
        max_ready_tests=config.max_ready_tests,
    )
    plan = build_wstg_engine_plan(profile)
    plan_ref = workspace.write_json("campaign-plan.json", plan.as_dict())

    decisions: list[AgenticCampaignDecision] = [
        AgenticCampaignDecision(
            step=1,
            action="build_wstg_campaign_plan",
            reason="canonical WSTG plan is required before live benchmark interaction",
            status="completed",
            evidence_refs=(plan_ref,),
        )
    ]
    observations: list[AgenticCampaignObservation] = []
    findings: list[AgenticCampaignFinding] = []
    observed_wstg_ids: set[str] = set()
    fetch = http_client or _default_http_client

    paths_to_fetch = list(_bounded_unique_paths(config.safe_paths, config.max_requests))
    root_observation: AgenticCampaignObservation | None = None
    api_observed = False
    script_count = 0
    form_count = 0
    link_count = 0
    request_index = 0

    for path in paths_to_fetch:
        request_index += 1
        url = _same_origin_url(config.normalized_base_url, path)
        decision = AgenticCampaignDecision(
            step=len(decisions) + 1,
            action="http_get_safe_path",
            reason=f"GET {path} is same-origin, read-only, and inside the local benchmark scope",
            status="started",
            wstg_ids=("WSTG-v42-INFO-06",),
        )
        decisions.append(decision)
        observation = fetch("GET", url, config.request_timeout_seconds)
        observations.append(observation)
        observation_ref = workspace.write_json(f"observations/http-{request_index:02d}.json", observation.as_dict())
        observed_wstg_ids.update(_wstg_ids_from_observation(path, observation))
        decisions[-1] = AgenticCampaignDecision(
            step=decision.step,
            action=decision.action,
            reason=decision.reason,
            status="completed" if observation.ok else "observed_error",
            wstg_ids=tuple(sorted(_wstg_ids_from_observation(path, observation))),
            evidence_refs=(observation_ref,),
        )
        if path == "/":
            root_observation = observation
        if _looks_like_json(observation):
            api_observed = True

    surface = _extract_surface(root_observation)
    surface_ref = workspace.write_json("surface/discovered-surface.json", surface)
    script_count = len(surface["scripts"])
    form_count = len(surface["forms"])
    link_count = len(surface["links"])
    if root_observation and root_observation.ok:
        observed_wstg_ids.update({"WSTG-v42-INFO-02", "WSTG-v42-INFO-05", "WSTG-v42-INFO-08"})
    if script_count:
        observed_wstg_ids.update({"WSTG-v42-CLNT-01", "WSTG-v42-CLNT-04"})
    if api_observed:
        observed_wstg_ids.update({"WSTG-v42-APIT-01", "WSTG-v42-INFO-06"})

    decisions.append(
        AgenticCampaignDecision(
            step=len(decisions) + 1,
            action="derive_surface_inventory",
            reason="HTML and JSON observations determine which review classes are supported by evidence",
            status="completed",
            wstg_ids=tuple(sorted({"WSTG-v42-INFO-05", "WSTG-v42-INFO-06", "WSTG-v42-INFO-08"})),
            evidence_refs=(surface_ref,),
        )
    )

    findings.extend(_candidate_findings(root_observation, api_observed, script_count, form_count, link_count))
    finding_ref = workspace.write_json("findings/candidate-findings.json", [finding.as_dict() for finding in findings])
    observed_wstg_ids.update(id_ for finding in findings for id_ in finding.wstg_ids)
    decisions.append(
        AgenticCampaignDecision(
            step=len(decisions) + 1,
            action="create_candidate_findings",
            reason="only evidence-backed observations are converted to candidate or manual-required findings",
            status="completed",
            wstg_ids=tuple(sorted({id_ for finding in findings for id_ in finding.wstg_ids})),
            evidence_refs=(finding_ref,),
        )
    )

    benchmark = compare_wstg_observations(sorted(observed_wstg_ids))
    benchmark_ref = workspace.write_json("reports/benchmark-comparison.json", benchmark)
    report_ref = workspace.write_text(
        "reports/campaign-report.md",
        _render_markdown_report(
            config=config,
            plan_ready=len(plan.ready_tests),
            plan_total=len(plan.planned_tests),
            observations=observations,
            findings=findings,
            benchmark=benchmark,
        ),
    )
    decisions_ref = workspace.write_text(
        "agent-decisions.jsonl",
        "".join(json.dumps(decision.as_dict(), sort_keys=True) + "\n" for decision in decisions),
    )
    observations_ref = workspace.write_json("observations/http-observations.json", [item.as_dict() for item in observations])

    decisions.append(
        AgenticCampaignDecision(
            step=len(decisions) + 1,
            action="compare_benchmark_coverage",
            reason="benchmark comparison explains detected, missed, and manual-required WSTG coverage",
            status="completed",
            wstg_ids=tuple(sorted(observed_wstg_ids)),
            evidence_refs=(benchmark_ref, report_ref, decisions_ref, observations_ref),
        )
    )

    completed = _utc_now()
    result = LocalJuiceShopCampaignResult(
        campaign_id=config.campaign_id,
        target_alias=profile.target_alias,
        base_url=config.normalized_base_url,
        evidence_dir=str(evidence_dir),
        started_at_utc=started,
        completed_at_utc=completed,
        request_count=len(observations),
        observed_wstg_ids=tuple(sorted(observed_wstg_ids)),
        decisions=tuple(decisions),
        observations=tuple(observations),
        findings=tuple(findings),
        benchmark_comparison=benchmark,
        artifacts=dict(workspace.artifacts),
    )
    result_ref = workspace.write_json("campaign-result.json", result.as_dict())
    workspace.artifacts[result_ref] = _sha256_file(evidence_dir / result_ref)
    _write_sha256s(evidence_dir)
    return result


def _candidate_findings(
    root_observation: AgenticCampaignObservation | None,
    api_observed: bool,
    script_count: int,
    form_count: int,
    link_count: int,
) -> list[AgenticCampaignFinding]:
    findings: list[AgenticCampaignFinding] = []
    if root_observation is not None:
        missing_headers = _missing_security_headers(root_observation.headers)
        if missing_headers:
            findings.append(
                AgenticCampaignFinding(
                    finding_id="js-candidate-security-header-gaps",
                    title="Security header gaps observed on local Juice Shop root response",
                    status="candidate",
                    severity="low",
                    confidence="medium",
                    wstg_ids=("WSTG-v42-CONF-01",),
                    evidence_refs=("observations/http-01.json",),
                    rationale="The root response did not include every baseline hardening header expected in a web application configuration review.",
                    next_step="Review response headers in the campaign report and decide whether the observation is expected for the intentionally vulnerable benchmark.",
                )
            )
    if api_observed:
        findings.append(
            AgenticCampaignFinding(
                finding_id="js-observed-api-surface",
                title="API surface observed during safe local benchmark discovery",
                status="observed",
                severity="informational",
                confidence="high",
                wstg_ids=("WSTG-v42-INFO-06", "WSTG-v42-APIT-01"),
                evidence_refs=("observations/http-observations.json",),
                rationale="At least one safe read-only API endpoint returned a JSON-like response inside the local benchmark scope.",
                next_step="Use later authenticated and safe-active adapters to expand API testing without embedding Juice Shop challenge solutions.",
            )
        )
    if script_count or form_count or link_count:
        findings.append(
            AgenticCampaignFinding(
                finding_id="js-client-side-review-required",
                title="Client-side application surface requires browser-backed review",
                status="manual_required",
                severity="informational",
                confidence="medium",
                wstg_ids=("WSTG-v42-CLNT-01", "WSTG-v42-CLNT-04"),
                evidence_refs=("surface/discovered-surface.json",),
                rationale="The benchmark exposes client-side scripts, links, or forms that require browser-backed validation before exploitability can be claimed.",
                next_step="Run the future browser adapter to collect DOM, route, storage, and JavaScript behavior evidence.",
            )
        )
    return findings


def _default_http_client(method: str, url: str, timeout: float) -> AgenticCampaignObservation:
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        method=method,
        headers={
            "User-Agent": "AOTP local Juice Shop benchmark runner",
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback-only checked by config
            body = response.read(262_144)
            headers = _redact_headers(dict(response.headers.items()))
            elapsed = int((time.monotonic() - started) * 1000)
            return AgenticCampaignObservation(
                method=method,
                url=url,
                status_code=int(response.status),
                reason=response.reason or "",
                headers=headers,
                content_type=response.headers.get("Content-Type", ""),
                body_sha256=hashlib.sha256(body).hexdigest(),
                body_excerpt=_safe_excerpt(body),
                body_size_bytes=len(body),
                elapsed_ms=elapsed,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(65_536)
        return AgenticCampaignObservation(
            method=method,
            url=url,
            status_code=int(exc.code),
            reason=str(exc.reason),
            headers=_redact_headers(dict(exc.headers.items())) if exc.headers else {},
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            body_sha256=hashlib.sha256(body).hexdigest(),
            body_excerpt=_safe_excerpt(body),
            body_size_bytes=len(body),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            error="http_error",
        )
    except OSError as exc:
        return AgenticCampaignObservation(
            method=method,
            url=url,
            status_code=0,
            reason="request_failed",
            headers={},
            content_type="",
            body_sha256=hashlib.sha256(b"").hexdigest(),
            body_excerpt="",
            body_size_bytes=0,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            error=exc.__class__.__name__,
        )


def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for name, value in headers.items():
        if name.lower() in _SENSITIVE_HEADER_NAMES:
            redacted[name] = "[redacted]"
        else:
            redacted[name] = value[:500]
    return redacted


def _safe_excerpt(body: bytes) -> str:
    text = body[:2000].decode("utf-8", errors="replace")
    text = re.sub(r"(?i)(authorization|cookie|token|password|secret)\s*[:=]\s*[^\s\"'<>]+", r"\1=[redacted]", text)
    return text[:5000]


def _validate_safe_path(path: str) -> None:
    parsed = urllib.parse.urlsplit(path)
    if parsed.scheme or parsed.netloc:
        raise JuiceShopCampaignError("safe paths must be relative to the benchmark origin")
    if not path.startswith("/"):
        raise JuiceShopCampaignError("safe paths must start with /")
    if ".." in parsed.path.split("/"):
        raise JuiceShopCampaignError("path traversal segments are not allowed in safe paths")


def _bounded_unique_paths(paths: Iterable[str], max_requests: int) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for path in paths:
        _validate_safe_path(path)
        if path not in seen:
            unique.append(path)
            seen.add(path)
        if len(unique) >= max_requests:
            break
    return tuple(unique)


def _same_origin_url(base_url: str, path: str) -> str:
    _validate_safe_path(path)
    candidate = urllib.parse.urljoin(base_url, path)
    base = urllib.parse.urlsplit(base_url)
    parsed = urllib.parse.urlsplit(candidate)
    if (parsed.scheme, parsed.hostname, parsed.port) != (base.scheme, base.hostname, base.port):
        raise JuiceShopCampaignError("derived URL escaped the local benchmark origin")
    return candidate


def _extract_surface(root_observation: AgenticCampaignObservation | None) -> dict[str, Any]:
    if root_observation is None or not root_observation.ok:
        return {"links": [], "scripts": [], "forms": [], "meta": {}, "markers": []}
    parser = _SurfaceParser()
    parser.feed(root_observation.body_excerpt)
    markers = []
    haystack = root_observation.body_excerpt.lower()
    for marker in ("owasp", "juice shop", "app-root", "score-board", "login"):
        if marker in haystack:
            markers.append(marker)
    return {
        "links": sorted(parser.links),
        "scripts": sorted(parser.scripts),
        "forms": parser.forms,
        "meta": dict(sorted(parser.meta.items())),
        "markers": sorted(markers),
    }


def _wstg_ids_from_observation(path: str, observation: AgenticCampaignObservation) -> set[str]:
    ids = {"WSTG-v42-INFO-06"}
    if path == "/" and observation.ok:
        ids.update({"WSTG-v42-INFO-02", "WSTG-v42-INFO-05", "WSTG-v42-INFO-08"})
    if path in {"/robots.txt", "/sitemap.xml"}:
        ids.add("WSTG-v42-INFO-01")
    if _looks_like_json(observation):
        ids.add("WSTG-v42-APIT-01")
    if observation.status_code >= 500:
        ids.add("WSTG-v42-ERRH-01")
    return ids


def _looks_like_json(observation: AgenticCampaignObservation) -> bool:
    content_type = observation.content_type.lower()
    excerpt = observation.body_excerpt.lstrip()
    return "json" in content_type or excerpt.startswith("{") or excerpt.startswith("[")


def _missing_security_headers(headers: Mapping[str, str]) -> tuple[str, ...]:
    present = {name.lower() for name in headers}
    expected = {"content-security-policy", "x-content-type-options", "referrer-policy"}
    return tuple(sorted(expected - present))


def _render_markdown_report(
    *,
    config: LocalJuiceShopCampaignConfig,
    plan_ready: int,
    plan_total: int,
    observations: list[AgenticCampaignObservation],
    findings: list[AgenticCampaignFinding],
    benchmark: dict[str, Any],
) -> str:
    lines = [
        "# Local Juice Shop Agentic Campaign Report",
        "",
        f"Campaign ID: `{config.campaign_id}`",
        f"Target: `{config.normalized_base_url}`",
        f"Authorization reference: `{config.authorization_reference}`",
        f"Plan coverage: `{plan_ready}` ready tests from `{plan_total}` canonical WSTG tests",
        f"Requests sent: `{len(observations)}`",
        "",
        "## Candidate findings",
        "",
    ]
    if not findings:
        lines.append("No candidate findings were created from the collected evidence.")
    for finding in findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"Status: `{finding.status}`",
                f"Severity: `{finding.severity}`",
                f"Confidence: `{finding.confidence}`",
                f"WSTG: `{', '.join(finding.wstg_ids)}`",
                f"Evidence: `{', '.join(finding.evidence_refs)}`",
                "",
                finding.rationale,
                "",
                f"Next step: {finding.next_step}",
                "",
            ]
        )
    coverage = benchmark["coverage"]
    lines.extend(
        [
            "## Benchmark comparison",
            "",
            f"Expected WSTG IDs: `{coverage['expected']}`",
            f"Detected WSTG IDs: `{coverage['detected']}`",
            f"Missed WSTG IDs: `{coverage['missed']}`",
            "",
            "This report is evidence-bound. Missed or manual-required items are not failures by themselves; they identify the next adapters and approvals required.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_sha256s(root: Path) -> None:
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "SHA256SUMS"):
        lines.append(f"{_sha256_file(path)}  {path.relative_to(root)}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a local Juice Shop agentic benchmark campaign")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--base-url", default=JUICE_SHOP_BASE_URL)
    parser.add_argument("--campaign-id", default="local-juice-shop-agentic-campaign")
    parser.add_argument("--max-requests", type=int, default=12)
    parser.add_argument("--max-ready-tests", type=int, default=30)
    args = parser.parse_args(argv)

    config = LocalJuiceShopCampaignConfig(
        evidence_dir=args.evidence_dir,
        base_url=args.base_url,
        campaign_id=args.campaign_id,
        max_requests=args.max_requests,
        max_ready_tests=args.max_ready_tests,
    )
    result = run_local_juice_shop_agentic_campaign(config)
    print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
