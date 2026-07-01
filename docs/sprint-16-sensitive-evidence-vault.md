# Sprint 16: Sensitive Evidence Vault and PoC Material Handling

Sprint 16 introduces a separate sensitive evidence plane for authorized campaign material that
must not enter normal evidence, git, ordinary logs, or public reports. Normal evidence uses opaque
vault handles and hashes. Raw sensitive material stays encrypted in a campaign-local vault and can
only be read through an audited authorization path.

## Implemented control model

- `public` and `restricted` evidence may remain in the normal evidence plane.
- `secret`, `poc_sensitive`, and `recipient_only` material requires the sensitive vault.
- `do_not_store` material is rejected before persistence.
- Vault records contain ciphertext, metadata, hashes, size, classification, artifact kind, and
  purpose. Metadata is checked so it cannot carry raw sensitive material.
- Every raw read logs the campaign id, active ROE campaign id, target alias, identity, purpose,
  handle, classification, decision, reason, and approval reference without logging the raw value.
- Secret-bearing tool interfaces resolve a vault handle in memory and deny argv or log surfaces
  that attempt to carry raw material.
- Classified PoC workspaces store reproducibility manifests that reference vault handles only.
- Sensitive annex export is separate from normal reports and requires explicit human approval.
- Repository safety now calls vault leakage validation to block tracked plaintext vault markers and
  generated vault paths.

## Files

- `src/aotp/evidence_classifier.py`
- `src/aotp/sensitive_vault.py`
- `src/aotp/vault_handles.py`
- `src/aotp/campaign_key_store.py`
- `src/aotp/agent_vault_access.py`
- `src/aotp/secret_bearing_tools.py`
- `src/aotp/poc_workspace.py`
- `src/aotp/sensitive_annex.py`
- `src/aotp/report_export_policy.py`
- `scripts/validate-vault-leakage.sh`

## Validation

Focused validation:

```bash
python -m pytest -q \
  tests/test_evidence_classifier.py \
  tests/test_sensitive_vault.py \
  tests/test_vault_handles.py \
  tests/test_campaign_key_store.py \
  tests/test_agent_vault_access.py \
  tests/test_secret_bearing_tools.py \
  tests/test_poc_workspace.py \
  tests/test_sensitive_annex.py \
  tests/test_vault_leakage_script.py
```

Full validation remains:

```bash
python -m compileall -q src tests
python -m pytest
bash scripts/validate-repository-safety.sh
make PYTHON="$PWD/.venv/bin/python" check
```

## Security notes

The vault uses the `cryptography` project Fernet recipe for symmetric authenticated encryption.
Fernet is suitable here because Sprint 16 stores bounded campaign proof material that fits in
memory, and the cryptography documentation notes that Fernet provides privacy and authenticity for
messages while requiring the key to remain secret.

Vault keys are local campaign secrets. They are written under operator-controlled local storage with
`0600` permissions and must not be committed or exported through normal evidence. Any handoff of
keys or annex material requires separate human-approved, out-of-band handling.
