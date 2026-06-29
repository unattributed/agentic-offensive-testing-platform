MODULE = {
    "name": "sbom_review",
    "supports": ("sbom", "manifest", "lockfile", "component_inventory"),
    "requires": ("provided_artifact", "artifact_hash"),
    "denies": ("unprovided_artifacts", "unverified_exploitability_claims"),
}
