from aotp.wstg.coverage import CoverageDisposition, CoverageTracker, choose_next_objective, render_coverage_report
from aotp.wstg.objective_generator import WSTGCampaignScope, generate_wstg_objectives
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase, build_default_strategy_map


def _objectives():
    scope = WSTGCampaignScope(
        campaign_id="campaign-17",
        target_alias="owned-app",
        base_url="https://example.test",
        authorization_reference="authz-17",
        operator_approved=True,
        allowed_phases=frozenset({WSTGPhase.PASSIVE, WSTGPhase.BROWSER}),
        approved_families=frozenset({
            ExecutableFamily.HTTP_METADATA,
            ExecutableFamily.WELL_KNOWN_TEXT,
            ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA,
        }),
    )
    return generate_wstg_objectives(scope, build_default_strategy_map())


def test_coverage_status_includes_all_dispositions_and_gaps():
    objectives = _objectives()
    tracker = CoverageTracker(objectives)
    tracker.mark(objectives[0], CoverageDisposition.TESTED, evidence_references=("evidence/root.json",))
    tracker.mark(objectives[1], CoverageDisposition.DENIED, reasons=("not approved",))

    summary = tracker.gap_summary()

    assert summary["statuses"]["tested"] == 1
    assert summary["statuses"]["denied"] == 1
    assert summary["statuses"]["deferred"] == len(objectives) - 2
    assert objectives[2].objective_id in summary["gaps"]


def test_agent_next_choice_explains_continue_and_stop():
    objectives = _objectives()
    tracker = CoverageTracker(objectives)

    decision = choose_next_objective(objectives, tracker, evidence_summaries=({"artifact_reference": "evidence/a.json"},))

    assert decision.action == "continue"
    assert decision.objective is not None
    assert "earliest approved uncovered" in decision.reason
    assert decision.evidence_inputs == ("evidence/a.json",)

    for objective in objectives:
        tracker.mark(objective, CoverageDisposition.TESTED, evidence_references=(f"evidence/{objective.objective_id}.json",))
    stop = choose_next_objective(objectives, tracker)
    assert stop.action == "stop"
    assert stop.objective is None


def test_coverage_report_renders_continue_or_stop_reason():
    objectives = _objectives()
    tracker = CoverageTracker(objectives)
    decision = choose_next_objective(objectives, tracker)

    report = render_coverage_report(tracker, campaign_id="campaign-17", target_alias="owned-app", decision=decision)

    assert "# WSTG Campaign Coverage Report" in report
    assert "Continue or stop" in report
    assert "WSTG-v42" in report


def test_next_objective_uses_defined_phase_order():
    objectives = generate_wstg_objectives(
        WSTGCampaignScope(
            campaign_id="campaign-17",
            target_alias="owned-app",
            base_url="https://example.test",
            authorization_reference="authz-17",
            operator_approved=True,
            allowed_phases=frozenset({WSTGPhase.BROWSER, WSTGPhase.AUTH}),
            approved_families=frozenset({ExecutableFamily.PLAYWRIGHT_PASSIVE_METADATA, ExecutableFamily.AUTH_BOUNDARY}),
            authenticated=True,
        ),
        build_default_strategy_map(),
    )
    tracker = CoverageTracker(objectives)

    decision = choose_next_objective(objectives, tracker)

    assert decision.objective is not None
    assert decision.objective.phase is WSTGPhase.BROWSER
