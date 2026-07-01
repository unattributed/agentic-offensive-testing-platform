from __future__ import annotations

import pytest

from aotp.evidence_classifier import (
    EvidenceClassification,
    EvidenceClassificationError,
    assert_may_store,
    assert_normal_evidence_safe,
    classify_mapping,
    classify_text,
    policy_for_classification,
)


def test_classifier_defines_sprint16_classifications():
    assert {item.value for item in EvidenceClassification} == {
        "public",
        "restricted",
        "secret",
        "poc_sensitive",
        "recipient_only",
        "do_not_store",
    }


def test_secret_like_output_is_classified_automatically():
    raw = "Authorization" + ": Bearer abcdefghijklmnop"
    result = classify_text(raw)
    assert result.classification is EvidenceClassification.SECRET
    assert result.vault_required is True
    assert result.normal_evidence_allowed is False


def test_private_key_marker_is_secret_without_literal_fixture_leak():
    raw = "-----" + "BEGIN PRIVATE KEY" + "-----\nsynthetic\n"
    result = classify_text(raw)
    assert result.classification is EvidenceClassification.SECRET


def test_do_not_store_material_fails_closed():
    result = classify_text("memory only do not store campaign material")
    assert result.classification is EvidenceClassification.DO_NOT_STORE
    assert result.may_store is False
    with pytest.raises(EvidenceClassificationError, match="cannot be persisted"):
        assert_may_store(result.classification)


def test_mapping_classification_detects_nested_sensitive_material():
    result = classify_mapping({"session" + "_id": "abcdefghi123456"})
    assert result.classification is EvidenceClassification.SECRET


def test_normal_evidence_blocks_secret_and_allows_public():
    assert_normal_evidence_safe("public metadata only")
    with pytest.raises(EvidenceClassificationError, match="not allowed in normal evidence"):
        assert_normal_evidence_safe("api" + "_key=abcdefghi123456")


def test_policy_for_classification_controls_storage_planes():
    assert policy_for_classification("restricted").normal_evidence_allowed is True
    assert policy_for_classification("poc_sensitive").vault_required is True
    assert policy_for_classification("recipient_only").may_store is True
