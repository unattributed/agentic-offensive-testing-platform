import json
import zipfile

import pytest

from aotp.integrations.osmap_source_review import OSMAPSourceReviewError, review_osmap_source


SOURCE = '''
from flask import Flask
app = Flask(__name__)

@app.route("/login", methods=["GET", "POST"])
def login():
    return "login"

@app.route("/account/settings", methods=["GET"])
def settings():
    require_auth()
    csrf_token = "redacted in source fixture"
    return "settings"

@app.route("/logout", methods=["POST"])
def logout():
    return "logout"
'''


def test_review_local_osmap_like_directory_without_copying_source(tmp_path):
    source = tmp_path / "osmap"
    source.mkdir()
    (source / "app.py").write_text(SOURCE, encoding="utf-8")
    (source / "binary.bin").write_bytes(b"\x00\x01")

    result = review_osmap_source(source, workspace=tmp_path)
    payload = json.dumps(result.as_dict(), sort_keys=True)

    assert result.source_kind == "directory"
    assert result.file_count == 1
    assert {candidate.path_pattern for candidate in result.route_candidates} >= {"/login", "/account/settings", "/logout"}
    assert "flask" in result.framework_indicators
    assert "require_auth" in result.auth_indicators
    assert "csrf_token =" not in payload
    assert result.ignored_file_reasons["binary.bin"] == "unsupported suffix"


def test_review_local_zip_fixture(tmp_path):
    archive = tmp_path / "osmap.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("osmap/app.py", SOURCE)

    result = review_osmap_source(archive, workspace=tmp_path)

    assert result.source_kind == "zip"
    assert result.route_candidates


def test_review_rejects_remote_urls_and_traversal_zip(tmp_path):
    with pytest.raises(OSMAPSourceReviewError):
        review_osmap_source("https://example.test/repo.zip")

    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.py", SOURCE)
    with pytest.raises(OSMAPSourceReviewError):
        review_osmap_source(archive, workspace=tmp_path)
