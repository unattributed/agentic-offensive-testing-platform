# SBOM and dependency review

The module accepts only provided SBOMs, manifests, lockfiles, container inventories, or component lists. Evidence records package, version, source artifact, hash, mapping, and confidence.

Component presence is not equivalent to reachable or exploitable application risk. Reports must state whether reachability and exploitability were actually verified.

Review is offline and limited to relative aliases in `provided_artifacts`. Component evidence
includes reproducible source and component hashes. Vulnerability mapping requires an explicitly
configured local data-source contract; implicit external lookup is forbidden.
