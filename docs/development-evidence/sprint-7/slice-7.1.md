# Sprint 7 Slice 7.1: artifact ingestion

Only relative artifact aliases listed in `provided_artifacts` pass policy. The offline reader
requires a regular non-symlink JSON file, applies a size limit, and records its SHA256.
