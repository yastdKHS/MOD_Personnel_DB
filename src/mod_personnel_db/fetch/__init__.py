"""FetchClient契約（Protocol）と実装。Phase7 Task16-3に対応する。

docs/api/package-design.md のfetch/節（Phase7 Task16-0で設計確定）が定める
「発令PDFを取得する（中核パイプラインの外側）」責務のうち、本Task16-3は
**HTTP経由の取得機構（転送層）のみ**を実装する。`PDFRepository`への登録・
`content_hash`による重複排除・`ftp/`経由の取得は、`fetch/`の広い責務として
package-design.mdが定めるが、いずれも本パッケージの現時点のScopeには
含まれない（将来タスクで追加する）。

`FetchClient`はPDF本文の解析を一切行わない（バイト列を取得するのみ）。
これは「Layout DetectorだけがPDF本文にアクセスできる」という
[architecture-contract.md 保証11]の適用（docs/api/package-design.md の
fetch/節参照）を維持するためである。

具象実装（`HTTPFetchClient`、`urllib`ベース）・テスト用モック実装
（`MockFetchClient`）はそれぞれ`fetch.client`・`fetch.mock`から提供する。
"""

from typing import Protocol

from mod_personnel_db.fetch.client import HTTPFetchClient
from mod_personnel_db.fetch.exceptions import (
    FetchContentTypeError,
    FetchError,
    FetchNetworkError,
    FetchStatusError,
    FetchTimeoutError,
    FetchValidationError,
)
from mod_personnel_db.fetch.messages import FetchRequest, FetchResult
from mod_personnel_db.fetch.mock import MockFetchClient, default_fetch_result


class FetchClient(Protocol):
    """PDF等のファイルをURLから取得するプロトコル層（バイト列のみを扱う）。"""

    def fetch(self, request: FetchRequest) -> FetchResult:
        """`request`が指すリソースを取得する（ダウンロードAPI）。"""
        ...


__all__ = [
    "FetchClient",
    "FetchContentTypeError",
    "FetchError",
    "FetchNetworkError",
    "FetchRequest",
    "FetchResult",
    "FetchStatusError",
    "FetchTimeoutError",
    "FetchValidationError",
    "HTTPFetchClient",
    "MockFetchClient",
    "default_fetch_result",
]
