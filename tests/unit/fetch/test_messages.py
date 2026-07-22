"""`FetchRequest`/`FetchResult`の検証（Phase7 Task16-3）。"""

import dataclasses
from datetime import UTC, datetime

import pytest

from mod_personnel_db.fetch import FetchRequest, FetchResult, FetchValidationError


def test_fetch_request_defaults() -> None:
    request = FetchRequest(url="https://example.mod.go.jp/order.pdf")

    assert request.timeout == 30.0
    assert request.expected_content_types is None
    assert request.headers == {}


def test_fetch_request_rejects_empty_url() -> None:
    with pytest.raises(FetchValidationError):
        FetchRequest(url="")


def test_fetch_request_rejects_non_positive_timeout() -> None:
    with pytest.raises(FetchValidationError):
        FetchRequest(url="https://example.mod.go.jp/order.pdf", timeout=0)


def test_fetch_request_is_frozen() -> None:
    request = FetchRequest(url="https://example.mod.go.jp/order.pdf")

    with pytest.raises(dataclasses.FrozenInstanceError):
        request.url = "https://other.example/"  # type: ignore[misc]


def test_fetch_result_holds_fields() -> None:
    result = FetchResult(
        url="https://example.mod.go.jp/order.pdf",
        status_code=200,
        content_type="application/pdf",
        body=b"%PDF-1.4",
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert result.status_code == 200
    assert result.body == b"%PDF-1.4"
