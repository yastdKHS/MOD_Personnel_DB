"""`HTTPFetchClient`の単体テスト（Phase7 Task16-3）。

`urllib.request.urlopen`は`unittest.mock`で差し替え、実際のネットワーク
接続は行わない（実ネットワークを用いた検証は`tests/integration/fetch/`が
担う）。
"""

import urllib.error
from collections.abc import Mapping
from email.message import Message
from types import TracebackType
from unittest.mock import MagicMock, patch

import pytest

from mod_personnel_db.fetch import (
    FetchContentTypeError,
    FetchNetworkError,
    FetchRequest,
    FetchStatusError,
    FetchTimeoutError,
    FetchValidationError,
)
from mod_personnel_db.fetch.client import HTTPFetchClient


class _FakeResponse:
    def __init__(self, *, status: int, headers: Mapping[str, str], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_returns_result_on_success(urlopen: MagicMock) -> None:
    urlopen.return_value = _FakeResponse(
        status=200, headers={"Content-Type": "application/pdf"}, body=b"%PDF-1.4"
    )
    client = HTTPFetchClient()

    result = client.fetch(FetchRequest(url="https://example.mod.go.jp/order.pdf"))

    assert result.status_code == 200
    assert result.content_type == "application/pdf"
    assert result.body == b"%PDF-1.4"


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_passes_headers_and_timeout(urlopen: MagicMock) -> None:
    urlopen.return_value = _FakeResponse(status=200, headers={}, body=b"x")
    client = HTTPFetchClient()
    request = FetchRequest(
        url="https://example.mod.go.jp/order.pdf",
        timeout=5.0,
        headers={"User-Agent": "mod-personnel-db-fetch/1.0"},
    )

    client.fetch(request)

    sent_request = urlopen.call_args.args[0]
    assert sent_request.get_header("User-agent") == "mod-personnel-db-fetch/1.0"
    assert urlopen.call_args.kwargs["timeout"] == 5.0


def test_fetch_rejects_non_http_scheme_without_network_call() -> None:
    client = HTTPFetchClient()

    with pytest.raises(FetchValidationError):
        client.fetch(FetchRequest(url="file:///etc/passwd"))


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_wraps_http_error_as_status_error_by_default(urlopen: MagicMock) -> None:
    urlopen.side_effect = urllib.error.HTTPError(
        "https://example.mod.go.jp/missing.pdf", 404, "Not Found", Message(), None
    )
    client = HTTPFetchClient()

    with pytest.raises(FetchStatusError) as excinfo:
        client.fetch(FetchRequest(url="https://example.mod.go.jp/missing.pdf"))

    assert excinfo.value.status_code == 404


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_accepts_configured_additional_status_codes(urlopen: MagicMock) -> None:
    urlopen.side_effect = urllib.error.HTTPError(
        "https://example.mod.go.jp/missing.pdf", 404, "Not Found", Message(), None
    )
    client = HTTPFetchClient(expected_status_codes=frozenset({200, 404}))

    result = client.fetch(FetchRequest(url="https://example.mod.go.jp/missing.pdf"))

    assert result.status_code == 404


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_wraps_timeout_error(urlopen: MagicMock) -> None:
    urlopen.side_effect = TimeoutError("timed out")
    client = HTTPFetchClient()

    with pytest.raises(FetchTimeoutError):
        client.fetch(FetchRequest(url="https://example.mod.go.jp/order.pdf"))


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_wraps_url_error_with_timeout_reason(urlopen: MagicMock) -> None:
    urlopen.side_effect = urllib.error.URLError(TimeoutError("timed out"))
    client = HTTPFetchClient()

    with pytest.raises(FetchTimeoutError):
        client.fetch(FetchRequest(url="https://example.mod.go.jp/order.pdf"))


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_wraps_url_error_as_network_error(urlopen: MagicMock) -> None:
    urlopen.side_effect = urllib.error.URLError(OSError("connection refused"))
    client = HTTPFetchClient()

    with pytest.raises(FetchNetworkError):
        client.fetch(FetchRequest(url="https://example.mod.go.jp/order.pdf"))


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_validates_content_type_success(urlopen: MagicMock) -> None:
    urlopen.return_value = _FakeResponse(
        status=200, headers={"Content-Type": "application/pdf; charset=binary"}, body=b"x"
    )
    client = HTTPFetchClient()
    request = FetchRequest(
        url="https://example.mod.go.jp/order.pdf", expected_content_types=("application/pdf",)
    )

    result = client.fetch(request)

    assert result.content_type == "application/pdf; charset=binary"


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_validates_content_type_failure(urlopen: MagicMock) -> None:
    urlopen.return_value = _FakeResponse(
        status=200, headers={"Content-Type": "text/html"}, body=b"<html></html>"
    )
    client = HTTPFetchClient()
    request = FetchRequest(
        url="https://example.mod.go.jp/order.pdf", expected_content_types=("application/pdf",)
    )

    with pytest.raises(FetchContentTypeError):
        client.fetch(request)


@patch("mod_personnel_db.fetch.client.urllib.request.urlopen")
def test_fetch_validates_content_type_failure_when_header_is_missing(urlopen: MagicMock) -> None:
    urlopen.return_value = _FakeResponse(status=200, headers={}, body=b"x")
    client = HTTPFetchClient()
    request = FetchRequest(
        url="https://example.mod.go.jp/order.pdf", expected_content_types=("application/pdf",)
    )

    with pytest.raises(FetchContentTypeError) as excinfo:
        client.fetch(request)

    assert excinfo.value.content_type is None
