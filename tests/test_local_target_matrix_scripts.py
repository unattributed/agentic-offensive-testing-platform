from pathlib import Path


def test_local_target_matrix_install_script_inventory_and_pending_crapi_status() -> None:
    script = Path("scripts/install-local-target-matrix.sh").read_text(encoding="utf-8")

    assert "--target crapi" in script
    assert "is_podman_emulated_docker" in script
    assert "crapi_live_runtime_status=pending_unsupported" in script
    assert "cleanup_partial_crapi_state" in script
    assert "local-target-state.json" in script
    assert "podman-compose" in script
    assert "Docker Compose" not in script


def test_crapi_reset_script_fails_fast_and_cleans_partial_state() -> None:
    script = Path("scripts/reset-local-target.sh").read_text(encoding="utf-8")

    assert "pending_unsupported" in script
    assert "cleanup_partial_crapi_state" in script
    assert "direct-container-cleanup.log" in script
    assert "post-cleanup-podman-ps.txt" in script
    assert "post-cleanup-listeners.txt" in script
    assert "local-target-state.json" in script
    assert "exit 3" in script
    assert "podman-compose" in script
    assert "up -d" not in script
    assert "docker-compose.yml" not in script
    assert "compose-pull.log" not in script


def test_local_target_matrix_validation_uses_repo_venv_and_marks_live_crapi_pending() -> None:
    script = Path("scripts/run-sprint18-followup-local-target-matrix-validation.sh").read_text(encoding="utf-8")

    assert 'PYTHON="$REPO/.venv/bin/python"' in script
    assert "tests/test_local_target_registry.py" in script
    assert "tests/test_crapi_local_profile.py" in script
    assert "tests/test_crapi_benchmark_mapping.py" in script
    assert "--live-crapi" in script
    assert "pending_unsupported" in script
