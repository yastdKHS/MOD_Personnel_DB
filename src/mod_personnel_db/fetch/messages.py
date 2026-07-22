"""`FetchClient`の入出力値オブジェクト（`FetchRequest`/`FetchResult`）。

`fetch/`パッケージ自身のローカルな値オブジェクトであり、`models/`の
ドメインモデルではない（本Task16-3ではPDF取得の転送機構のみを実装し、
`PDFRepository`への登録・重複排除は将来タスクに委ねるため、`models/`
への依存を導入しない）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime

from mod_personnel_db.fetch.exceptions import FetchValidationError


@dataclass(frozen=True, slots=True)
class FetchRequest:
    """取得対象を表す不変の値オブジェクト。"""

    url: str
    timeout: float = 30.0
    expected_content_types: tuple[str, ...] | None = None
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.url == "":
            raise FetchValidationError("url must not be empty")
        if self.timeout <= 0:
            raise FetchValidationError("timeout must be > 0")


@dataclass(frozen=True, slots=True)
class FetchResult:
    """取得結果を表す不変の値オブジェクト。"""

    url: str
    status_code: int
    content_type: str | None
    body: bytes
    fetched_at: datetime


__all__ = ["FetchRequest", "FetchResult"]
