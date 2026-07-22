"""`InMemoryFTPClient`を用いた実ファイルシステムとの結合テスト（Phase7 Task16-1）。

`tests/unit/ftp/test_mock_client.py`が個々のメソッドを単体で検証するのに
対し、本テストは実際の一時ディレクトリ（`tmp_path`）に配置した複数の
実ファイルを対象に、`connect → upload → list_remote → download → disconnect`
という`FTPClient`Protocolのライフサイクル全体を通しで検証する。
"""

from pathlib import Path

import pytest

from mod_personnel_db.ftp import FTPClient, FTPConnectionError, InMemoryFTPClient


def test_full_lifecycle_round_trips_multiple_real_files(tmp_path: Path) -> None:
    client: FTPClient = InMemoryFTPClient()

    source_dir = tmp_path / "outbox"
    source_dir.mkdir()
    order_a = source_dir / "order_a.pdf"
    order_b = source_dir / "order_b.pdf"
    order_a.write_bytes(b"order-a-body")
    order_b.write_bytes(b"order-b-body")

    client.connect()
    client.upload(str(order_a), "personnel_orders/2026/order_a.pdf")
    client.upload(str(order_b), "personnel_orders/2026/order_b.pdf")

    remote_entries = client.list_remote("personnel_orders/2026")
    assert set(remote_entries) == {
        "personnel_orders/2026/order_a.pdf",
        "personnel_orders/2026/order_b.pdf",
    }

    download_dir = tmp_path / "inbox"
    download_dir.mkdir()
    downloaded_a = download_dir / "order_a.pdf"
    client.download("personnel_orders/2026/order_a.pdf", str(downloaded_a))

    assert downloaded_a.read_bytes() == order_a.read_bytes()

    client.disconnect()
    with pytest.raises(FTPConnectionError):
        client.list_remote("personnel_orders/2026")
