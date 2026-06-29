"""Campaign objective ordering."""

from typing import Any


def schedule(objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(objectives, key=lambda item: (item.get("priority", 100), item.get("id", "")))
