import pytest

from aotp.wstg.browser_metadata import BrowserMetadataError, map_browser_forms, map_browser_routes
from aotp.wstg.error_handling import ErrorHandlingPlanError, build_error_handling_plan
from aotp.wstg.input_boundary import InputBoundaryError, InputPayloadClass, build_input_boundary_plan


def test_error_handling_plan_enforces_budget_and_stop_conditions():
    plan = build_error_handling_plan("wstg-v42-errh-01", max_requests=2, planned_requests=1)

    assert "stack_trace_observed" in plan.stop_conditions
    with pytest.raises(ErrorHandlingPlanError):
        build_error_handling_plan("wstg-v42-errh-01", max_requests=1, planned_requests=2)


def test_input_boundary_plan_rejects_state_changing_mode():
    plan = build_input_boundary_plan(
        "wstg-v42-inpv-01",
        approved_payload_classes=(InputPayloadClass.METADATA_ONLY, InputPayloadClass.LENGTH_BOUNDARY),
        max_requests=2,
    )

    assert plan.planned_requests == 2
    with pytest.raises(InputBoundaryError):
        build_input_boundary_plan(
            "wstg-v42-inpv-01",
            approved_payload_classes=(InputPayloadClass.METADATA_ONLY, InputPayloadClass.LENGTH_BOUNDARY),
            max_requests=1,
        )


def test_browser_route_and_form_metadata_stays_on_origin_and_maps_categories():
    routes = map_browser_routes("https://example.test", ("/", "/login"))
    forms = map_browser_forms(
        "https://example.test",
        ({"action": "/login", "method": "post", "input_names": ("username", "password")},),
    )

    assert routes[1].wstg_categories == ("INFO", "ATHN")
    assert forms[0].wstg_categories == ("INPV", "ATHN")
    assert forms[0].method == "POST"


def test_browser_metadata_denies_out_of_origin_links_and_forms():
    with pytest.raises(BrowserMetadataError):
        map_browser_routes("https://example.test", ("https://evil.test/",))
    with pytest.raises(BrowserMetadataError):
        map_browser_forms("https://example.test", ({"action": "https://evil.test/login"},))
