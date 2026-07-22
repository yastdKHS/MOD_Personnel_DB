"""`HTTPFetchClient`と実HTTP/ソケットスタックとの結合テスト（Phase7 Task16-3）。

`tests/unit/fetch/test_client.py`は`urllib.request.urlopen`をモックで
差し替えて呼び出し規約を検証するのに対し、本テストは`urllib`を一切
モックせず、実際にローカルで起動したHTTPサーバ（標準ライブラリの
`http.server`、外部依存なし）へ接続することで、`HTTPFetchClient`が
実ネットワーク・実HTTPプロトコルの下で正しく動作することを確認する。
"""

import http.server
import socket
import threading
from collections.abc import Iterator

import pytest

from mod_personnel_db.fetch import (
    FetchNetworkError,
    FetchRequest,
    FetchStatusError,
    HTTPFetchClient,
)

_PDF_BODY = b"%PDF-1.4 sample-order-body"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/order.pdf":
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(_PDF_BODY)))
            self.end_headers()
            self.wfile.write(_PDF_BODY)
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def server_url() -> Iterator[str]:
    httpd = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        thread.join()


def test_fetch_retrieves_real_response_over_http(server_url: str) -> None:
    client = HTTPFetchClient()
    request = FetchRequest(
        url=f"{server_url}/order.pdf", expected_content_types=("application/pdf",)
    )

    result = client.fetch(request)

    assert result.status_code == 200
    assert result.content_type == "application/pdf"
    assert result.body == _PDF_BODY


def test_fetch_raises_status_error_for_real_404_response(server_url: str) -> None:
    client = HTTPFetchClient()
    request = FetchRequest(url=f"{server_url}/missing.pdf")

    with pytest.raises(FetchStatusError) as excinfo:
        client.fetch(request)

    assert excinfo.value.status_code == 404


def _unused_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def test_fetch_raises_network_error_for_unreachable_port() -> None:
    client = HTTPFetchClient()
    request = FetchRequest(url=f"http://127.0.0.1:{_unused_tcp_port()}/order.pdf", timeout=2.0)

    with pytest.raises(FetchNetworkError):
        client.fetch(request)
