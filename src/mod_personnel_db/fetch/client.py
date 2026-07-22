"""`FetchClient`の標準HTTP実装。Python標準ライブラリの`urllib`のみに依存する
（新規の外部依存を追加しない）。

`http://`/`https://`以外のURLスキームは明示的に拒否する（`urllib.request`は
既定で`file://`等も開けてしまうため、意図しないローカルファイル読み取りを
防ぐ安全対策）。PDF本文の解析は一切行わない（バイト列を取得するのみ）。
"""

from __future__ import annotations

import urllib.error
import urllib.request
from datetime import UTC, datetime
from urllib.parse import urlparse

from mod_personnel_db.fetch.exceptions import (
    FetchContentTypeError,
    FetchNetworkError,
    FetchStatusError,
    FetchTimeoutError,
    FetchValidationError,
)
from mod_personnel_db.fetch.messages import FetchRequest, FetchResult

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_DEFAULT_EXPECTED_STATUS_CODES = frozenset({200})


def _normalize_content_type(content_type: str | None) -> str | None:
    if content_type is None:
        return None
    return content_type.split(";")[0].strip().lower()


class HTTPFetchClient:
    """`urllib.request`へ委譲する標準HTTP実装（`FetchClient`Protocolを満たす）。"""

    def __init__(
        self, expected_status_codes: frozenset[int] = _DEFAULT_EXPECTED_STATUS_CODES
    ) -> None:
        self._expected_status_codes = expected_status_codes

    def fetch(self, request: FetchRequest) -> FetchResult:
        _validate_scheme(request.url)
        http_request = urllib.request.Request(request.url, headers=dict(request.headers))

        status_code, content_type, body = self._open(http_request, request)

        self._validate_status(status_code, request.url)
        _validate_content_type(content_type, request)

        return FetchResult(
            url=request.url,
            status_code=status_code,
            content_type=content_type,
            body=body,
            fetched_at=datetime.now(UTC),
        )

    def _open(
        self, http_request: urllib.request.Request, request: FetchRequest
    ) -> tuple[int, str | None, bytes]:
        try:
            with urllib.request.urlopen(http_request, timeout=request.timeout) as response:
                return response.status, response.headers.get("Content-Type"), response.read()
        except urllib.error.HTTPError as exc:
            content_type = exc.headers.get("Content-Type") if exc.headers is not None else None
            return exc.code, content_type, exc.read()
        except TimeoutError as exc:
            raise FetchTimeoutError(f"タイムアウトしました: {request.url}") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise FetchTimeoutError(f"タイムアウトしました: {request.url}") from exc
            raise FetchNetworkError(f"ネットワークエラーが発生しました: {request.url}") from exc

    def _validate_status(self, status_code: int, url: str) -> None:
        if status_code not in self._expected_status_codes:
            raise FetchStatusError(
                f"unexpected HTTP status {status_code} for {url}", status_code=status_code
            )


def _validate_scheme(url: str) -> None:
    scheme = urlparse(url).scheme
    if scheme not in _ALLOWED_SCHEMES:
        raise FetchValidationError(f"unsupported URL scheme {scheme!r}: {url}")


def _validate_content_type(content_type: str | None, request: FetchRequest) -> None:
    if request.expected_content_types is None:
        return
    expected = {value.strip().lower() for value in request.expected_content_types}
    if _normalize_content_type(content_type) not in expected:
        raise FetchContentTypeError(
            f"unexpected Content-Type {content_type!r} for {request.url}",
            content_type=content_type,
        )


__all__ = ["HTTPFetchClient"]
