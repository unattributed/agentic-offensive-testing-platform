# Safe demonstration script

1. Show that the repository is private and the example files contain placeholders.
2. Run `make check`.
3. Run `aotp list-modules` and `aotp list-cases`.
4. Run `aotp dry-run --scope config/scope.example.yaml`.
5. Plan and run `authorized-webapp-campaign.example.yaml` without `--live`.
6. Inspect ignored state, event records, and evidence manifests.
7. Generate an evidence-only report.
8. Attempt live mode with the example scope and show the policy denial.
9. Explain the private profile, authorization checklist, human gate, and network-silent live stubs.

The demonstration contacts no target and uses no real assessment data.
