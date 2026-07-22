"""テスト用の`MockFetchClient`実装。実際のネットワーク接続を一切行わない。"""

from __future__ import annotations

from datetime import UTC, datetime

from mod_personnel_db.fetch.messages import FetchRequest, FetchResult


class MockFetchClient:
    """呼び出し順に事前設定した`FetchResult`を返す、またはデフォルトを生成するモック実装。"""

    def __init__(self, responses: list[FetchResult] | None = None) -> None:
        self._responses = list(responses) if responses is not None else None
        self.calls: list[FetchRequest] = []

    def fetch(self, request: FetchRequest) -> FetchResult:
        self.calls.append(request)
        if self._responses is not None:
            return self._responses[len(self.calls) - 1]
        return default_fetch_result(request.url)


def default_fetch_result(url: str, *, body: bytes = b"%PDF-1.4 dummy") -> FetchResult:
    """既定のダミー`FetchResult`を生成する（`MockFetchClient`の既定応答）。"""
    return FetchResult(
        url=url,
        status_code=200,
        content_type="application/pdf",
        body=body,
        fetched_at=datetime.now(UTC),
    )


__all__ = ["MockFetchClient", "default_fetch_result"]
