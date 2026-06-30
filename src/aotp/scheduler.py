"""Deterministic dependency-aware campaign objective scheduling."""

from __future__ import annotations

from typing import Any


def schedule(objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item["id"]): item for item in objectives}
    remaining = set(by_id)
    completed: set[str] = set()
    ordered: list[dict[str, Any]] = []
    while remaining:
        ready = [
            by_id[objective_id]
            for objective_id in remaining
            if set(by_id[objective_id].get("depends_on", [])) <= completed
        ]
        if not ready:
            raise ValueError("campaign objectives cannot be scheduled due to dependency cycle")
        ready.sort(key=lambda item: (int(item.get("priority", 100)), str(item["id"])))
        selected = ready[0]
        objective_id = str(selected["id"])
        ordered.append(selected)
        remaining.remove(objective_id)
        completed.add(objective_id)
    return ordered
