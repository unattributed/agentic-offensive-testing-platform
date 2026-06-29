from copy import deepcopy
from pathlib import Path

import pytest

from aotp.config import load_yaml


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def example_scope(project_root: Path) -> dict:
    return deepcopy(load_yaml(project_root / "config/scope.example.yaml").data)
