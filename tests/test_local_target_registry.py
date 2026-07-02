from aotp.lab_targets.registry import (
    build_local_target_registry,
    get_local_target_entry,
    implemented_local_target_aliases,
)


def test_local_target_registry_contains_juice_shop_and_planned_crapi() -> None:
    registry = build_local_target_registry()
    aliases = {entry.target_alias for entry in registry}

    assert aliases == {"local-juice-shop", "local-crapi"}
    assert set(implemented_local_target_aliases()) == {"local-juice-shop"}
    assert get_local_target_entry("local-crapi").category == "modern-api-and-business-logic"
    assert get_local_target_entry("local-crapi").lifecycle == "planned"
    assert get_local_target_entry("local-crapi").implemented_live_target is False
    assert get_local_target_entry("local-juice-shop").network_exposure == "loopback-only"


def test_local_target_registry_entries_are_metadata_only_and_reset_required() -> None:
    for entry in build_local_target_registry():
        as_dict = entry.as_dict()
        assert as_dict["target_alias"].startswith("local-")
        assert as_dict["network_exposure"] == "loopback-only"
        assert as_dict["reset_required_before_campaign"] is True
        assert as_dict["benchmark_manifest"].startswith("aotp.benchmarks.")
        assert "osmap" not in repr(as_dict).lower()


def test_crapi_is_registered_but_not_a_proven_live_target() -> None:
    crapi = get_local_target_entry("local-crapi")

    assert crapi.lifecycle == "planned"
    assert crapi.implemented_live_target is False
    assert any("live runtime pending" in note for note in crapi.notes)


def test_unknown_local_target_alias_is_rejected() -> None:
    try:
        get_local_target_entry("local-osmap")
    except KeyError as exc:
        assert "unknown local target alias" in str(exc)
    else:
        raise AssertionError("unknown local target alias was accepted")
