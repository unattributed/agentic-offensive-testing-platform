"""Canonical SBOM review module contract."""

from ..sbom_review import VULNERABILITY_MAPPING_CONTRACT


MODULE = {
    "name": "sbom_review",
    "supports": ("sbom", "manifest", "lockfile", "component_inventory"),
    "requires": ("provided_artifact", "artifact_hash"),
    "denies": ("unprovided_artifacts", "unverified_exploitability_claims"),
    "vulnerability_mapping": VULNERABILITY_MAPPING_CONTRACT,
}
