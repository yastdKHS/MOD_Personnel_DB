"""テスト用のインメモリ`FTPClient`実装。実際のネットワーク接続を一切行わない。

`fetch/`・`services/`（いずれも未実装、Phase7 Task16-0でftp/への依存を確定済み）が
将来、実FTPサーバなしに結合テストを書けるようにするためのモックである。
"""

from __future__ import annotations

from pathlib import Path

from mod_personnel_db.ftp.exceptions import FTPConnectionError, FTPTransferError


class InMemoryFTPClient:
    """メモリ上の辞書へ転送するモック実装（`FTPClient`Protocolを満たす）。"""

    def __init__(self) -> None:
        self._connected = False
        self._files: dict[str, bytes] = {}
        self.uploaded: list[tuple[str, str]] = []
        self.downloaded: list[tuple[str, str]] = []

    def connect(self) -> None:
        self._connected = True

    def upload(self, local_path: str, remote_path: str) -> None:
        self._require_connected()
        try:
            data = Path(local_path).read_bytes()
        except OSError as exc:
            raise FTPTransferError(
                f"アップロードに失敗しました: {local_path} -> {remote_path}"
            ) from exc
        self._files[remote_path] = data
        self.uploaded.append((local_path, remote_path))

    def download(self, remote_path: str, local_path: str) -> None:
        self._require_connected()
        if remote_path not in self._files:
            raise FTPTransferError(f"リモートファイルが存在しません: {remote_path}")
        Path(local_path).write_bytes(self._files[remote_path])
        self.downloaded.append((remote_path, local_path))

    def list_remote(self, remote_dir: str) -> tuple[str, ...]:
        self._require_connected()
        prefix = remote_dir.rstrip("/") + "/"
        return tuple(name for name in self._files if name.startswith(prefix))

    def disconnect(self) -> None:
        self._connected = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise FTPConnectionError("connect()が呼び出されていません。")


__all__ = ["InMemoryFTPClient"]
