from pathlib import Path


def test_core_wstg_engine_has_no_osmap_dependency(project_root: Path):
    core_files = [
        path for path in (project_root / "src" / "aotp" / "wstg").glob("*.py")
        if path.name != "__init__.py"
    ]

    offenders = []
    for path in core_files:
        text = path.read_text().lower()
        if "osmap" in text:
            offenders.append(str(path.relative_to(project_root)))

    assert offenders == []
