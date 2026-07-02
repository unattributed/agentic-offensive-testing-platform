"""Generic agentic WSTG live campaign harness."""

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
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from aotp.wstg import build_wstg_engine_plan

from .campaign_state import CampaignDecision, CampaignFinding, WSTGLiveCampaignState
from .evidence_writer import CampaignEvidenceWriter
from .execution_planner import CampaignAction, plan_campaign_actions
from .proof_requests import ProofRequest, build_proof_requests
from .target_runtime import CampaignTargetRuntime, build_juice_shop_target_runtime, runtime_from_local_target_registry

ActionExecutor = Callable[[CampaignAction, CampaignTargetRuntime, float], "WSTGLiveObservation"]

_SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
}


class WSTGLiveCampaignError(ValueError):
    """Raised when a generic live campaign is unsafe or cannot run."""


@dataclass(frozen=True)
class WSTGLiveCampaignConfig:
    """Configuration for a generic WSTG live campaign run."""

    evidence_dir: Path | str
    target_runtime: CampaignTargetRuntime
    campaign_id: str = "generic-wstg-live-campaign"
    request_timeout_seconds: float = 5.0
    max_actions: int | None = None
    proof_request_limit: int = 20

    def __post_init__(self) -> None:
        if self.request_timeout_seconds <= 0 or self.request_timeout_seconds > 30:
            raise WSTGLiveCampaignError("request timeout must be positive and bounded")
        if self.max_actions is not None and (self.max_actions < 1 or self.max_actions > self.target_runtime.max_actions):
            raise WSTGLiveCampaignError("max_actions must be within target runtime bounds")
        if self.proof_request_limit < 1 or self.proof_request_limit > 100:
            raise WSTGLiveCampaignError("proof_request_limit must be between 1 and 100")


@dataclass(frozen=True)
class WSTGLiveObservation:
    """Redacted observation produced by an approved campaign action."""

    action_id: str
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
    wstg_ids: tuple[str, ...]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400 and self.error is None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WSTGLiveCampaignResult:
    """Completed generic WSTG live campaign result."""

    campaign_id: str
    target_alias: str
    base_url: str
    evidence_dir: str
    request_count: int
    observed_wstg_ids: tuple[str, ...]
    decisions: tuple[CampaignDecision, ...]
    observations: tuple[WSTGLiveObservation, ...]
    findings: tuple[CampaignFinding, ...]
    proof_requests: tuple[ProofRequest, ...]
    benchmark_comparison: dict[str, Any] | None
    artifacts: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "target_alias": self.target_alias,
            "base_url": self.base_url,
            "evidence_dir": self.evidence_dir,
            "request_count": self.request_count,
            "observed_wstg_ids": list(self.observed_wstg_ids),
            "decisions": [decision.as_dict() for decision in self.decisions],
            "observations": [observation.as_dict() for observation in self.observations],
            "findings": [finding.as_dict() for finding in self.findings],
            "proof_requests": [request.as_dict() for request in self.proof_requests],
            "benchmark_comparison": self.benchmark_comparison,
            "artifacts": dict(self.artifacts),
        }


def run_wstg_live_campaign(
    config: WSTGLiveCampaignConfig,
    *,
    action_executor: ActionExecutor | None = None,
) -> WSTGLiveCampaignResult:
    """Run a bounded generic WSTG campaign against an approved target runtime."""

    evidence_dir = Path(config.evidence_dir).expanduser().resolve()
    writer = CampaignEvidenceWriter(evidence_dir)
    runtime = config.target_runtime
    plan = build_wstg_engine_plan(runtime.build_wstg_profile(campaign_id=config.campaign_id))
    plan_ref = writer.write_json("campaign/plan.json", plan.as_dict())
    execution_plan = plan_campaign_actions(plan, runtime)
    action_ref = writer.write_json("campaign/action-queue.json", execution_plan.as_dict())
    state = WSTGLiveCampaignState(
        campaign_id=config.campaign_id,
        target_alias=runtime.target_alias,
        base_url=runtime.normalized_base_url,
        planned_objectives=len(plan.planned_tests),
        queued_actions=len(execution_plan.actions),
    )
    state.record_decision(
        CampaignDecision(
            step=1,
            agent="campaign-lead-agent",
            action="build_generic_wstg_plan",
            reason="generic WSTG planning must complete before live target interaction",
            status="completed",
            evidence_refs=(plan_ref, action_ref),
        )
    )
    fetch = action_executor or default_http_get_executor
    observations: list[WSTGLiveObservation] = []
    action_limit = config.max_actions or runtime.max_actions
    for action in execution_plan.actions[:action_limit]:
        started_step = len(state.decisions) + 1
        state.record_decision(
            CampaignDecision(
                step=started_step,
                agent="execution-planner-agent",
                action=action.action_type,
                reason=action.reason,
                status="started",
                wstg_ids=action.wstg_ids,
            )
        )
        observation = fetch(action, runtime, config.request_timeout_seconds)
        observations.append(observation)
        observation_ref = writer.write_json(f"observations/{action.action_id}.json", observation.as_dict())
        state.executed_actions += 1
        state.mark_observed(observation.wstg_ids)
        state.decisions[-1] = CampaignDecision(
            step=started_step,
            agent="execution-planner-agent",
            action=action.action_type,
            reason=action.reason,
            status="completed" if observation.ok else "observed_error",
            wstg_ids=observation.wstg_ids,
            evidence_refs=(observation_ref,),
        )
    surface = _extract_surface(next((item for item in observations if urllib.parse.urlsplit(item.url).path in {"", "/"}), None))
    surface_ref = writer.write_json("surface/discovered-surface.json", surface)
    state.record_decision(
        CampaignDecision(
            step=len(state.decisions) + 1,
            agent="evidence-auditor-agent",
            action="derive_surface_inventory",
            reason="observed HTML and JSON metadata determine which proof is still missing",
            status="completed",
            wstg_ids=tuple(sorted(state.observed_wstg_ids)),
            evidence_refs=(surface_ref,),
        )
    )
    findings = tuple(_candidate_findings(observations, surface))
    finding_ref = writer.write_json("findings/candidate-findings.json", [finding.as_dict() for finding in findings])
    state.finding_ids.extend(finding.finding_id for finding in findings)
    state.record_decision(
        CampaignDecision(
            step=len(state.decisions) + 1,
            agent="evidence-auditor-agent",
            action="create_evidence_bound_candidates",
            reason="observations can only become candidates or proof requests, not validated claims",
            status="completed",
            wstg_ids=tuple(sorted({wstg_id for finding in findings for wstg_id in finding.wstg_ids})),
            evidence_refs=(finding_ref,),
        )
    )
    proof_requests = build_proof_requests(plan, state.observed_wstg_ids, limit=config.proof_request_limit)
    proof_ref = writer.write_json("proof-requests/proof-requests.json", [request.as_dict() for request in proof_requests])
    state.proof_request_ids.extend(request.proof_request_id for request in proof_requests)
    state.record_decision(
        CampaignDecision(
            step=len(state.decisions) + 1,
            agent="campaign-lead-agent",
            action="request_missing_proof",
            reason="unproven objectives remain proof requests instead of reportable vulnerabilities",
            status="completed",
            wstg_ids=tuple(request.wstg_id for request in proof_requests),
            evidence_refs=(proof_ref,),
        )
    )
    benchmark = runtime.benchmark_comparator(sorted(state.observed_wstg_ids)) if runtime.benchmark_comparator else None
    benchmark_ref = writer.write_json("reports/benchmark-comparison.json", benchmark or {"benchmark": "not_configured"})
    state_ref = writer.write_json("state/campaign-state.json", state.as_dict())
    decisions_ref = writer.write_jsonl("agent-decisions.jsonl", [decision.as_dict() for decision in state.decisions])
    observation_index_ref = writer.write_json("observations/http-observations.json", [item.as_dict() for item in observations])
    report_ref = writer.write_text(
        "reports/campaign-report.md",
        _render_report(
            campaign_id=config.campaign_id,
            target_alias=runtime.target_alias,
            plan_total=len(plan.planned_tests),
            ready_total=len(plan.ready_tests),
            observations=observations,
            findings=findings,
            proof_requests=proof_requests,
            benchmark=benchmark,
        ),
    )
    state.record_decision(
        CampaignDecision(
            step=len(state.decisions) + 1,
            agent="campaign-lead-agent",
            action="write_campaign_package",
            reason="campaign package records observations, candidate findings, proof gaps, benchmark comparison, and hashes",
            status="completed",
            wstg_ids=tuple(sorted(state.observed_wstg_ids)),
            evidence_refs=(benchmark_ref, state_ref, decisions_ref, observation_index_ref, report_ref),
        )
    )
    final_state_ref = writer.write_json("state/final-campaign-state.json", state.as_dict())
    writer.write_sha256s()
    result = WSTGLiveCampaignResult(
        campaign_id=config.campaign_id,
        target_alias=runtime.target_alias,
        base_url=runtime.normalized_base_url,
        evidence_dir=str(evidence_dir),
        request_count=len(observations),
        observed_wstg_ids=tuple(sorted(state.observed_wstg_ids)),
        decisions=tuple(state.decisions),
        observations=tuple(observations),
        findings=findings,
        proof_requests=proof_requests,
        benchmark_comparison=benchmark,
        artifacts={**writer.artifacts, final_state_ref: writer.artifacts[final_state_ref]},
    )
    result_ref = writer.write_json("campaign-result.json", result.as_dict())
    writer.artifacts[result_ref] = writer.artifacts[result_ref]
    writer.write_sha256s()
    return result


def default_http_get_executor(action: CampaignAction, runtime: CampaignTargetRuntime, timeout: float) -> WSTGLiveObservation:
    """Execute a same-origin GET action and return redacted evidence."""

    if action.method != "GET" or action.path not in runtime.safe_paths:
        raise WSTGLiveCampaignError("executor only accepts planned safe GET actions")
    url = _same_origin_url(runtime.normalized_base_url, action.path)
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "AOTP generic WSTG live campaign", "Accept": "text/html,application/json;q=0.9,*/*;q=0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - runtime validates scope
            body = response.read(262_144)
            return WSTGLiveObservation(
                action_id=action.action_id,
                method="GET",
                url=url,
                status_code=int(response.status),
                reason=response.reason or "",
                headers=_redact_headers(dict(response.headers.items())),
                content_type=response.headers.get("Content-Type", ""),
                body_sha256=hashlib.sha256(body).hexdigest(),
                body_excerpt=_safe_excerpt(body),
                body_size_bytes=len(body),
                elapsed_ms=int((time.monotonic() - started) * 1000),
                wstg_ids=action.wstg_ids,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(65_536)
        return WSTGLiveObservation(
            action_id=action.action_id,
            method="GET",
            url=url,
            status_code=int(exc.code),
            reason=str(exc.reason),
            headers=_redact_headers(dict(exc.headers.items())) if exc.headers else {},
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            body_sha256=hashlib.sha256(body).hexdigest(),
            body_excerpt=_safe_excerpt(body),
            body_size_bytes=len(body),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            wstg_ids=action.wstg_ids,
            error="http_error",
        )
    except OSError as exc:
        return WSTGLiveObservation(
            action_id=action.action_id,
            method="GET",
            url=url,
            status_code=0,
            reason="request_failed",
            headers={},
            content_type="",
            body_sha256=hashlib.sha256(b"").hexdigest(),
            body_excerpt="",
            body_size_bytes=0,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            wstg_ids=action.wstg_ids,
            error=exc.__class__.__name__,
        )


def run_local_juice_shop_generic_wstg_campaign(
    evidence_dir: Path | str,
    *,
    action_executor: ActionExecutor | None = None,
    max_actions: int = 5,
    max_ready_tests: int = 30,
) -> WSTGLiveCampaignResult:
    """Run the generic harness against the supported local Juice Shop runtime."""

    runtime = build_juice_shop_target_runtime(max_actions=max_actions, max_ready_tests=max_ready_tests)
    return run_wstg_live_campaign(
        WSTGLiveCampaignConfig(
            evidence_dir=evidence_dir,
            target_runtime=runtime,
            campaign_id="local-juice-shop-generic-wstg",
            max_actions=max_actions,
        ),
        action_executor=action_executor,
    )


def _candidate_findings(observations: list[WSTGLiveObservation], surface: dict[str, Any]) -> list[CampaignFinding]:
    findings: list[CampaignFinding] = []
    root_observation = next((item for item in observations if urllib.parse.urlsplit(item.url).path in {"", "/"}), None)
    if root_observation is not None:
        missing_headers = _missing_security_headers(root_observation.headers)
        if missing_headers:
            findings.append(
                CampaignFinding(
                    finding_id="candidate-security-header-gaps",
                    title="Security header gaps observed on root response",
                    state="candidate",
                    severity="low",
                    confidence="medium",
                    wstg_ids=("WSTG-v42-CONF-01",),
                    evidence_refs=(f"observations/{root_observation.action_id}.json",),
                    rationale="The root response did not include every baseline hardening header expected in a web application configuration review.",
                    next_step="Collect browser and proxy evidence before this can become a validated finding.",
                )
            )
    if any(_looks_like_json(item) for item in observations):
        findings.append(
            CampaignFinding(
                finding_id="observed-api-surface",
                title="API surface observed during governed WSTG discovery",
                state="observed",
                severity="informational",
                confidence="high",
                wstg_ids=("WSTG-v42-INFO-06", "WSTG-v42-APIT-01"),
                evidence_refs=("observations/http-observations.json",),
                rationale="At least one read-only API endpoint returned a JSON-like response inside the approved target scope.",
                next_step="Use the API discovery agent to collect route provenance and validation evidence before impact is claimed.",
            )
        )
    if surface.get("scripts") or surface.get("forms") or surface.get("links"):
        findings.append(
            CampaignFinding(
                finding_id="browser-workflow-proof-required",
                title="Client-side application surface requires stateful browser proof",
                state="needs_more_evidence",
                severity="informational",
                confidence="medium",
                wstg_ids=("WSTG-v42-CLNT-01", "WSTG-v42-CLNT-04"),
                evidence_refs=("surface/discovered-surface.json",),
                rationale="The campaign observed client-side assets that require browser-backed workflow evidence before validation.",
                next_step="Assign the browser workflow agent to collect DOM, route, storage, and interaction evidence.",
            )
        )
    return findings


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


def _extract_surface(root_observation: WSTGLiveObservation | None) -> dict[str, Any]:
    if root_observation is None or not root_observation.ok:
        return {"links": [], "scripts": [], "forms": [], "meta": {}, "markers": []}
    parser = _SurfaceParser()
    parser.feed(root_observation.body_excerpt)
    markers: list[str] = []
    lowered = root_observation.body_excerpt.lower()
    if "app-root" in lowered:
        markers.append("single-page-application-marker")
    if "juice shop" in lowered:
        markers.append("benchmark-identity-marker")
    return {
        "links": sorted(parser.links),
        "scripts": sorted(parser.scripts),
        "forms": parser.forms,
        "meta": dict(sorted(parser.meta.items())),
        "markers": markers,
    }


def _missing_security_headers(headers: Mapping[str, str]) -> tuple[str, ...]:
    lower = {name.lower() for name in headers}
    expected = ("content-security-policy", "x-content-type-options", "referrer-policy")
    return tuple(name for name in expected if name not in lower)


def _looks_like_json(observation: WSTGLiveObservation) -> bool:
    return "json" in observation.content_type.lower() or observation.body_excerpt.lstrip().startswith(("{", "["))


def _redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for name, value in headers.items():
        redacted[name] = "[redacted]" if name.lower() in _SENSITIVE_HEADER_NAMES else value[:500]
    return redacted


def _safe_excerpt(body: bytes) -> str:
    text = body[:2000].decode("utf-8", errors="replace")
    text = re.sub(r"(?i)(authorization|cookie|token|password|secret)\s*[:=]\s*[^\s\"'<>]+", r"\1=[redacted]", text)
    return text[:5000]


def _same_origin_url(base_url: str, path: str) -> str:
    candidate = urllib.parse.urljoin(base_url, path)
    base = urllib.parse.urlsplit(base_url)
    parsed = urllib.parse.urlsplit(candidate)
    if (parsed.scheme, parsed.hostname, parsed.port) != (base.scheme, base.hostname, base.port):
        raise WSTGLiveCampaignError("derived URL escaped the approved target origin")
    return candidate


def _render_report(
    *,
    campaign_id: str,
    target_alias: str,
    plan_total: int,
    ready_total: int,
    observations: list[WSTGLiveObservation],
    findings: tuple[CampaignFinding, ...],
    proof_requests: tuple[ProofRequest, ...],
    benchmark: dict[str, Any] | None,
) -> str:
    lines = [
        f"# Generic WSTG campaign report: {campaign_id}",
        "",
        f"Target: `{target_alias}`",
        f"Planned WSTG tests: {plan_total}",
        f"Ready WSTG tests: {ready_total}",
        f"Executed governed actions: {len(observations)}",
        f"Candidate or observed findings: {len(findings)}",
        f"Proof requests: {len(proof_requests)}",
        "",
        "## Boundary",
        "",
        "This Sprint 19 harness runs bounded read-only campaign actions and records missing proof instead of validating unsupported exploit claims.",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("No candidate findings were produced by this bounded campaign slice.")
    for finding in findings:
        lines.extend(
            [
                f"### {finding.title}",
                "",
                f"State: `{finding.state}`",
                f"Severity: `{finding.severity}`",
                f"Confidence: `{finding.confidence}`",
                f"WSTG: {', '.join(finding.wstg_ids)}",
                f"Evidence: {', '.join(finding.evidence_refs)}",
                f"Next step: {finding.next_step}",
                "",
            ]
        )
    lines.extend(["## Proof requests", ""])
    for request in proof_requests[:10]:
        lines.extend([f"- `{request.wstg_id}`: {request.reason} ({request.requested_agent})"])
    if benchmark:
        coverage = benchmark.get("coverage", {})
        lines.extend(["", "## Benchmark comparison", "", f"Detected: {coverage.get('detected', 'n/a')}", f"Missed: {coverage.get('missed', 'n/a')}"])
    lines.append("")
    return "\n".join(lines)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the generic WSTG live campaign harness")
    parser.add_argument("--target", default="local-juice-shop", help="implemented local target alias")
    parser.add_argument("--evidence-dir", required=True, help="directory for campaign evidence")
    parser.add_argument("--max-actions", type=int, default=5, help="maximum bounded actions to execute")
    args = parser.parse_args(argv)
    runtime = runtime_from_local_target_registry(args.target)
    config = WSTGLiveCampaignConfig(evidence_dir=args.evidence_dir, target_runtime=runtime, max_actions=args.max_actions)
    result = run_wstg_live_campaign(config)
    print(json.dumps({"campaign_id": result.campaign_id, "target_alias": result.target_alias, "request_count": result.request_count, "evidence_dir": result.evidence_dir}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main())
