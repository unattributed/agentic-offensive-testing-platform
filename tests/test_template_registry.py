import json

import pytest
import yaml

from aotp.cli import main
from aotp.config import ConfigError, load_yaml
from aotp.template_registry import hash_template_bundle, parse_template_registry, verify_template_source


def test_example_registry_is_valid_but_sources_are_disabled(project_root):
    loaded = load_yaml(project_root / "config/template-sources.example.yaml")
    sources = parse_template_registry(loaded.data)
    failures = verify_template_source(sources["nuclei-curated-candidate"], loaded.path)
    assert "template source is disabled" in failures
    assert "template source license has not been reviewed" in failures


def test_pinned_local_template_bundle_can_be_verified(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "passive.yaml").write_text("id: reviewed-passive-check\n", encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "sources": [
            {
                "source_id": "reviewed-nuclei",
                "kind": "nuclei_yaml",
                "repository": "https://github.com/projectdiscovery/nuclei-templates",
                "commit_sha": "a" * 40,
                "license_spdx": "MIT",
                "license_reviewed": True,
                "enabled": True,
                "local_path": "bundle",
                "sha256": hash_template_bundle(bundle),
                "signature_required": True,
                "allowed_template_ids": ["reviewed-passive-check"],
                "allowed_capabilities": ["passive_http"],
                "denied_capabilities": [
                    "code_execution",
                    "credential_attack",
                    "destructive_payload",
                    "target_discovery",
                ],
            }
        ],
    }
    registry_path = tmp_path / "private-registry.yaml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    parsed = parse_template_registry(registry)["reviewed-nuclei"]
    assert verify_template_source(parsed, registry_path) == []

    (bundle / "passive.yaml").write_text("id: changed-after-review\n", encoding="utf-8")
    assert verify_template_source(parsed, registry_path) == [
        "template bundle SHA256 does not match registry"
    ]


def test_registry_rejects_unsafe_path_and_missing_denials(project_root):
    data = load_yaml(project_root / "config/template-sources.example.yaml").data
    data["sources"][0]["local_path"] = "../outside"
    data["sources"][0]["denied_capabilities"] = ["code_execution"]
    with pytest.raises(ConfigError, match="must stay within"):
        parse_template_registry(data)


def test_template_source_verify_cli(tmp_path, monkeypatch, capsys):
    bundle = tmp_path / "reviewed.yar"
    bundle.write_text("rule reviewed_placeholder { condition: false }\n", encoding="utf-8")
    registry = {
        "schema_version": "1.0",
        "sources": [
            {
                "source_id": "reviewed-yara",
                "kind": "yara",
                "repository": "https://github.com/virustotal/yara",
                "commit_sha": "b" * 40,
                "license_spdx": "BSD-3-Clause",
                "license_reviewed": True,
                "enabled": True,
                "local_path": "reviewed.yar",
                "sha256": hash_template_bundle(bundle),
                "signature_required": False,
                "allowed_template_ids": ["reviewed_placeholder"],
                "allowed_capabilities": ["provided_artifact_classification"],
                "denied_capabilities": [
                    "code_execution",
                    "credential_attack",
                    "destructive_payload",
                    "target_discovery",
                ],
            }
        ],
    }
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert main(["template-source-verify", "--registry", str(registry_path), "--source", "reviewed-yara"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "valid": True,
        "source": "reviewed-yara",
        "failures": [],
    }
