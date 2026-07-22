"""`MockFetchClient`の単体テスト（Phase7 Task16-3）。"""

from mod_personnel_db.fetch import FetchRequest, FetchResult, MockFetchClient, default_fetch_result


def test_default_fetch_result_has_pdf_content_type() -> None:
    result = default_fetch_result("https://example.mod.go.jp/order.pdf")

    assert result.status_code == 200
    assert result.content_type == "application/pdf"
    assert result.url == "https://example.mod.go.jp/order.pdf"


def test_mock_returns_default_when_no_responses_configured() -> None:
    client = MockFetchClient()
    request = FetchRequest(url="https://example.mod.go.jp/order.pdf")

    result = client.fetch(request)

    assert isinstance(result, FetchResult)
    assert result.url == request.url


def test_mock_records_calls() -> None:
    client = MockFetchClient()
    request = FetchRequest(url="https://example.mod.go.jp/order.pdf")

    client.fetch(request)

    assert client.calls == [request]


def test_mock_returns_preconfigured_responses_in_order() -> None:
    preset_a = default_fetch_result("https://a.example/", body=b"A")
    preset_b = default_fetch_result("https://b.example/", body=b"B")
    client = MockFetchClient(responses=[preset_a, preset_b])

    first = client.fetch(FetchRequest(url="https://a.example/"))
    second = client.fetch(FetchRequest(url="https://b.example/"))

    assert first is preset_a
    assert second is preset_b
