import pytest

from aotp.evidence_classifier import EvidenceClassification
from aotp.wstg.session_management import (
    SessionManagementError,
    build_session_observation,
    classify_session_text,
)


def test_session_material_is_classified_secret():
    header_name = "Cookie"
    token_name = "_".join(("session", "id"))
    token_value = "abcdef" + "1234567890"
    classification = classify_session_text(f"{header_name}: {token_name}={token_value}")

    assert classification is EvidenceClassification.SECRET


def test_session_observation_excludes_raw_values():
    observation = build_session_observation(
        cookies={"session": {"secure": True, "httponly": True, "samesite": True}},
        vault_handle="vault://campaign/handle",
    )

    assert observation.raw_values_included is False
    assert observation.cookie_names == ("session",)


def test_session_observation_rejects_raw_cookie_values():
    with pytest.raises(SessionManagementError):
        build_session_observation(cookies={"session": {"secure": True, "value": True}})
