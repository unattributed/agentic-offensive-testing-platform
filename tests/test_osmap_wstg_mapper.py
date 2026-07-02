import pytest

from aotp.integrations.osmap_route_map import build_osmap_route_auth_map
from aotp.integrations.osmap_source_review import review_osmap_source
from aotp.integrations.osmap_wstg_mapper import OSMAPWSTGMappingError, map_osmap_routes_to_wstg_requests
from aotp.wstg.execution_adapter import WSTGAdapterKind
from aotp.wstg.objective_generator import WSTGCampaignScope
from aotp.wstg.strategy_map import ExecutableFamily, WSTGPhase


SOURCE = '''
@app.route("/account/settings", methods=["GET"])
def settings():
    require_auth()
    session.get("user")
    return "settings"
'''


def _route_map(tmp_path):
    root = tmp_path / "osmap"
    root.mkdir()
    (root / "app.py").write_text(SOURCE, encoding="utf-8")
    return build_osmap_route_auth_map(review_osmap_source(root, workspace=tmp_path))


def _scope(**overrides):
    values = dict(
        campaign_id="campaign-18",
        target_alias="owned-app",
        base_url="https://example.test",
        authorization_reference="authz-18",
        operator_approved=True,
        allowed_phases=frozenset({WSTGPhase.AUTH}),
        approved_families=frozenset({ExecutableFamily.SESSION_MANAGEMENT, ExecutableFamily.AUTH_BOUNDARY}),
        authenticated=True,
        allow_session_material=True,
    )
    values.update(overrides)
    return WSTGCampaignScope(**values)


def test_osmap_routes_map_through_sprint17f_adapter_contract(tmp_path):
    candidates = map_osmap_routes_to_wstg_requests(_route_map(tmp_path), _scope(), approval_reference="approval-18")

    assert candidates
    request = candidates[0].request
    assert request.adapter_kind is WSTGAdapterKind.APP_SPECIFIC_RUNNER
    assert request.executor_name == "osmap_authenticated_wstg"
    assert request.arguments["path_pattern"] == "/account/settings"
    assert candidates[0].source_limitations


def test_osmap_mapping_denies_without_authenticated_scope(tmp_path):
    with pytest.raises(OSMAPWSTGMappingError):
        map_osmap_routes_to_wstg_requests(
            _route_map(tmp_path),
            _scope(authenticated=False),
            approval_reference="approval-18",
        )
