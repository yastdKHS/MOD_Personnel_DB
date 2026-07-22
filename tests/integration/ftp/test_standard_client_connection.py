"""`StandardFTPClient`と実ソケットスタックとの結合テスト（Phase7 Task16-1）。

`tests/unit/ftp/test_standard_client.py`は`ftplib.FTP`をモックで差し替えて
呼び出し規約を検証するのに対し、本テストは`ftplib`を一切モックせず、実際に
未使用のTCPポートへ接続を試みることで、`StandardFTPClient.connect()`が
実ネットワークの接続失敗（`ConnectionRefusedError`）を`FTPConnectionError`
へ正しく変換することを確認する（外部のFTPサーバは不要）。
"""

import socket

import pytest

from mod_personnel_db.ftp import FTPConnectionConfig, FTPConnectionError
from mod_personnel_db.ftp.client import StandardFTPClient


def _unused_tcp_port() -> int:
    """バインド直後にソケットを閉じ、誰も listen していないポート番号を返す。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def test_connect_to_unreachable_port_raises_ftp_connection_error() -> None:
    config = FTPConnectionConfig(host="127.0.0.1", port=_unused_tcp_port(), timeout=2.0)
    client = StandardFTPClient(config)

    with pytest.raises(FTPConnectionError):
        client.connect()
