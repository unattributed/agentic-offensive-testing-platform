from pathlib import Path


def test_reset_script_enforces_fresh_loopback_container() -> None:
    script = Path("scripts/juice-shop-local-reset.sh").read_text(encoding="utf-8")

    assert "127.0.0.1" in script
    assert "-p \"$HOST:$PORT:3000\"" in script
    assert "rm -f \"$CONTAINER_NAME\"" in script
    assert "run -d" in script
    assert "inspect --format '{{json .Mounts}}'" in script
    assert "persistent or host mounts are not allowed" in script
    assert "passwordless sudo is required" in script
    assert "current_user=\"$(id -un)\"" in script


def test_install_script_inventories_before_installing() -> None:
    script = Path("scripts/install-local-juice-shop-benchmark.sh").read_text(encoding="utf-8")

    assert "preflight-inventory.txt" in script
    assert "apt-get install -y docker.io" in script
    assert "pull \"$IMAGE\"" in script
    assert "juice-shop-local-reset.sh" in script
    assert "this benchmark must be installed and managed by user foo" in script


def test_scripts_support_parrot_podman_docker_emulation() -> None:
    install_script = Path("scripts/install-local-juice-shop-benchmark.sh").read_text(encoding="utf-8")
    reset_script = Path("scripts/juice-shop-local-reset.sh").read_text(encoding="utf-8")

    for script in (install_script, reset_script):
        assert "docker.io/bkimminich/juice-shop" in script
        assert "podman" in script
        assert "podman-docker-emulation" in script
        assert "select_container_tool" in script
        assert "container_cmd=(\"$container_tool\")" in script
        assert "docker_service=not_required_for_$container_style" in script or "Docker and Podman are both supported" in script


def test_validation_runner_is_silent_unless_live_flags_are_requested() -> None:
    script = Path("scripts/run-sprint18-followup-local-juice-shop-validation.sh").read_text(encoding="utf-8")

    assert "--install-local-juice-shop" in script
    assert "--live-juice-shop" in script
    assert "tests/test_juice_shop_local_profile.py" in script
    assert "scripts/install-local-juice-shop-benchmark.sh" in script
    assert "scripts/juice-shop-local-reset.sh" in script
