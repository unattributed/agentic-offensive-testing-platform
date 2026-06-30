# Sprint 6 Slice 6.4: private corpus references

The `fuzzing-corpus-reference` command hashes a private local corpus and writes a mode-`0600`
reference containing only alias, SHA256, byte count, payload count, safe payload class, schema,
and source type. Paths and payload values are excluded.

Dry-run evidence records the corpus alias and validated reference, never corpus contents.
