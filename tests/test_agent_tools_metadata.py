from __future__ import annotations

import hashlib

import pytest

from aotp.agent_tools.http_metadata import (
    NativeToolError,
    fetch_http_metadata,
    fetch_well_known_metadata,
)
from aotp.agent_tools.tls_metadata import fetch_tls_metadata


class FakeHttpResponse:
    status = 200
    headers = {
        "Content-Type": "text/plain",
        "Set-Cookie": "must-not-enter-evidence",
        "Server": "test",
    }

    def __init__(self, body=b"safe metadata body"):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.body


def test_http_metadata_uses_get_hashes_body_and_excludes_cookie():
    captured = []

    def opener(request, timeout):
        captured.append((request.full_url, request.method, timeout))
        return FakeHttpResponse()

    result = fetch_http_metadata(
        "https://mail.example.invalid/",
        opener=opener,
    )
    assert result.request_count == 1
    assert captured == [("https://mail.example.invalid/", "GET", 10)]
    assert result.result["body_sha256"] == hashlib.sha256(
        b"safe metadata body"
    ).hexdigest()
    assert "set-cookie" not in result.result["headers"]


def test_well_known_metadata_checks_exact_two_paths():
    paths = []

    def opener(request, timeout):
        paths.append(request.full_url)
        return FakeHttpResponse()

    result = fetch_well_known_metadata(
        "https://mail.example.invalid",
        opener=opener,
    )
    assert result.request_count == 2
    assert paths == [
        "https://mail.example.invalid/robots.txt",
        "https://mail.example.invalid/.well-known/security.txt",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:pass@mail.example.invalid/",
        "https://mail.example.invalid/?token=value",
    ],
)
def test_http_metadata_rejects_unsafe_urls(url):
    with pytest.raises(NativeToolError):
        fetch_http_metadata(url, opener=lambda *_args, **_kwargs: FakeHttpResponse())


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeTlsSocket(FakeConnection):
    def getpeercert(self, binary_form=False):
        if binary_form:
            return b"certificate"
        return {
            "subject": ((("commonName", "mail.example.invalid"),),),
            "issuer": ((("commonName", "test-ca"),),),
            "notBefore": "before",
            "notAfter": "after",
            "subjectAltName": (("DNS", "mail.example.invalid"),),
        }

    def cipher(self):
        return ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)

    def version(self):
        return "TLSv1.3"


class FakeContext:
    def wrap_socket(self, connection, server_hostname):
        assert isinstance(connection, FakeConnection)
        assert server_hostname == "mail.example.invalid"
        return FakeTlsSocket()


def test_tls_metadata_records_cert_hash_without_raw_certificate():
    captured = {}

    def connect(address, timeout):
        captured["address"] = address
        captured["timeout"] = timeout
        return FakeConnection()

    result = fetch_tls_metadata(
        "mail.example.invalid",
        443,
        "mail.example.invalid",
        connection_factory=connect,
        context_factory=FakeContext,
    )
    assert result.request_count == 1
    assert captured == {
        "address": ("mail.example.invalid", 443),
        "timeout": 10,
    }
    assert result.result["tls_version"] == "TLSv1.3"
    assert result.result["certificate_sha256"] == hashlib.sha256(
        b"certificate"
    ).hexdigest()
    assert "certificate_der" not in result.result
    assert b"certificate" not in result.result.values()


def test_tls_metadata_requires_sni_to_match_host():
    with pytest.raises(NativeToolError, match="matching SNI"):
        fetch_tls_metadata("mail.example.invalid", 443, "other.example.invalid")
