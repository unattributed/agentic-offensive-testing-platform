import pytest

from aotp.scheduler import schedule


def test_scheduler_respects_dependencies_before_priority():
    objectives = [
        {"id": "dependent", "priority": 1, "depends_on": ["foundation"]},
        {"id": "independent", "priority": 5, "depends_on": []},
        {"id": "foundation", "priority": 10, "depends_on": []},
    ]
    assert [item["id"] for item in schedule(objectives)] == [
        "independent",
        "foundation",
        "dependent",
    ]


def test_scheduler_is_deterministic_for_equal_priority():
    objectives = [
        {"id": "b", "priority": 1, "depends_on": []},
        {"id": "a", "priority": 1, "depends_on": []},
    ]
    assert [item["id"] for item in schedule(objectives)] == ["a", "b"]


def test_scheduler_rejects_unschedulable_graph():
    objectives = [
        {"id": "a", "priority": 1, "depends_on": ["b"]},
        {"id": "b", "priority": 1, "depends_on": ["a"]},
    ]
    with pytest.raises(ValueError, match="dependency cycle"):
        schedule(objectives)
