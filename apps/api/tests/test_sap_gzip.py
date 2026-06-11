"""Tests for SAP connector gzip decompression in _get_text().

Guards two post-R20 behaviours:
1. A response body with Content-Encoding: gzip is decompressed before decode.
2. A response body starting with \\x1f\\x8b (gzip magic bytes) is decompressed
   even when the gateway omits the Content-Encoding header.
3. A plain (non-gzip) response passes through unchanged.
"""

from __future__ import annotations

import gzip


from app.connectors.sap.live_connector import SAPLiveConfig, SAPLiveConnector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _connector() -> SAPLiveConnector:
    return SAPLiveConnector(
        SAPLiveConfig(host="sandbox.api.sap.com", api_key="test-key", api_base_path="s4hanacloud")
    )


class _FakeHeaders:
    def __init__(self, mapping: dict | None = None):
        self._m = mapping or {}

    def get(self, key: str, default: str = "") -> str:
        return self._m.get(key, default)


class _FakeResponse:
    def __init__(self, body: bytes, headers: dict | None = None):
        self._body = body
        self.headers = _FakeHeaders(headers)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


def _make_opener(response: _FakeResponse):
    return type("FakeOpener", (), {"open": staticmethod(lambda req, timeout=None: response)})()


# ---------------------------------------------------------------------------
# gzip via Content-Encoding header
# ---------------------------------------------------------------------------

def test_gzip_header_triggers_decompression() -> None:
    payload = '{"value": "hello from SAP"}'
    compressed = gzip.compress(payload.encode("utf-8"))

    c = _connector()
    c._opener = _make_opener(_FakeResponse(compressed, {"Content-Encoding": "gzip"}))

    result = c._get_text("https://example.com/fake")
    assert result == payload


# ---------------------------------------------------------------------------
# gzip via magic bytes (no Content-Encoding header)
# ---------------------------------------------------------------------------

def test_gzip_magic_bytes_trigger_decompression_without_header() -> None:
    payload = '{"value": "magic bytes trigger"}'
    compressed = gzip.compress(payload.encode("utf-8"))
    assert compressed[:2] == b"\x1f\x8b"

    c = _connector()
    c._opener = _make_opener(_FakeResponse(compressed, {}))  # no Content-Encoding

    result = c._get_text("https://example.com/fake")
    assert result == payload


# ---------------------------------------------------------------------------
# Non-gzip passthrough
# ---------------------------------------------------------------------------

def test_plain_utf8_response_passes_through_unchanged() -> None:
    payload = '{"d": {"results": []}}'

    c = _connector()
    c._opener = _make_opener(_FakeResponse(payload.encode("utf-8"), {}))

    result = c._get_text("https://example.com/fake")
    assert result == payload


def test_plain_response_not_starting_with_magic_bytes_passes_through() -> None:
    payload = "<ODataServiceDocument/>"  # XML, no gzip

    c = _connector()
    c._opener = _make_opener(_FakeResponse(payload.encode("utf-8"), {}))

    result = c._get_text("https://example.com/fake")
    assert result == payload


# ---------------------------------------------------------------------------
# Gzip round-trip fidelity — unicode content
# ---------------------------------------------------------------------------

def test_gzip_unicode_content_decoded_correctly() -> None:
    payload = '{"name": "Müller GmbH & Co. KG"}'
    compressed = gzip.compress(payload.encode("utf-8"))

    c = _connector()
    c._opener = _make_opener(_FakeResponse(compressed, {"Content-Encoding": "gzip"}))

    result = c._get_text("https://example.com/fake")
    assert "Müller" in result
