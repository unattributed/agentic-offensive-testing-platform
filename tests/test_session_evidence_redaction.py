import json

import pytest

from aotp.session_evidence import (
    SessionEvidenceError,
    SessionStorageRoute,
    assert_public_session_record_safe,
    build_session_evidence_record,
)


SECRET_COOKIE = "session" + "id=super-secret-cookie-value"
VAULT_HANDLE = "vault://campaign-18/secret/session-cookie/0123456789abcdef0123456789abcdef"


def test_public_metadata_record_hashes_without_raw_session_value():
    record = build_session_evidence_record(
        material_kind="cookie",
        alias="login-cookie",
        raw_value=SECRET_COOKIE,
        storage_route=SessionStorageRoute.PUBLIC_METADATA_ONLY,
        source="login response",
    )

    payload = json.dumps(record.as_dict(), sort_keys=True)
    assert record.value_sha256
    assert SECRET_COOKIE not in payload
    assert "super-secret" not in payload
    assert_public_session_record_safe(record)


def test_memory_only_and_do_not_store_never_persist_hash_or_handle():
    memory = build_session_evidence_record(
        material_kind="csrf",
        alias="csrf-one",
        raw_value="csrf-token-value",
        storage_route="memory_only",
        source="form parse",
    )
    denied = build_session_evidence_record(
        material_kind="session_identifier",
        alias="sid-one",
        raw_value="session-id-value",
        storage_route="do_not_store",
        source="post logout",
    )

    assert memory.as_dict()["value_sha256"] is None
    assert denied.as_dict()["value_sha256"] is None


def test_vaulted_material_requires_valid_vault_handle():
    with pytest.raises(SessionEvidenceError):
        build_session_evidence_record(
            material_kind="cookie",
            alias="cookie-one",
            raw_value=SECRET_COOKIE,
            storage_route="vaulted",
            source="login response",
        )

    record = build_session_evidence_record(
        material_kind="cookie",
        alias="cookie-one",
        raw_value=SECRET_COOKIE,
        storage_route="vaulted",
        source="login response",
        vault_handle=VAULT_HANDLE,
    )
    assert record.vault_handle == VAULT_HANDLE
