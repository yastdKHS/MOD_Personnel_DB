"""`FTPClient`の標準実装。Python標準ライブラリの`ftplib`のみに依存する（新規の外部依存を追加しない）。

バイト列・パス文字列のみを扱うプロトコル層に徹し、ドメインモデル（`models/`）を
一切importしない（docs/api/package-design.md のftp/節「依存禁止」）。
"""

from __future__ import annotations

import ftplib
from pathlib import Path

from mod_personnel_db.ftp.config import FTPConnectionConfig
from mod_personnel_db.ftp.exceptions import FTPConnectionError, FTPTransferError


class StandardFTPClient:
    """`ftplib.FTP`へ委譲する標準FTP実装（`FTPClient`Protocolを満たす）。"""

    def __init__(self, config: FTPConnectionConfig) -> None:
        self._config = config
        self._connection: ftplib.FTP | None = None

    def connect(self) -> None:
        """FTPサーバへ接続しログインする。接続済みの場合は何もしない。"""
        if self._connection is not None:
            return
        connection = ftplib.FTP()
        try:
            connection.connect(self._config.host, self._config.port, timeout=self._config.timeout)
            connection.login(self._config.username, self._config.password)
            connection.set_pasv(self._config.passive)
        except (OSError, ftplib.Error) as exc:
            raise FTPConnectionError(
                f"FTPサーバへの接続に失敗しました: {self._config.host}:{self._config.port}"
            ) from exc
        self._connection = connection

    def upload(self, local_path: str, remote_path: str) -> None:
        """`local_path`のファイルをバイナリモードで`remote_path`へアップロードする。"""
        connection = self._require_connection()
        try:
            with Path(local_path).open("rb") as source:
                connection.storbinary(f"STOR {remote_path}", source)
        except (OSError, ftplib.Error) as exc:
            raise FTPTransferError(
                f"アップロードに失敗しました: {local_path} -> {remote_path}"
            ) from exc

    def download(self, remote_path: str, local_path: str) -> None:
        """`remote_path`のファイルをバイナリモードで`local_path`へダウンロードする。"""
        connection = self._require_connection()
        try:
            with Path(local_path).open("wb") as destination:
                connection.retrbinary(f"RETR {remote_path}", destination.write)
        except (OSError, ftplib.Error) as exc:
            raise FTPTransferError(
                f"ダウンロードに失敗しました: {remote_path} -> {local_path}"
            ) from exc

    def list_remote(self, remote_dir: str) -> tuple[str, ...]:
        """`remote_dir`配下のエントリ名一覧を返す。"""
        connection = self._require_connection()
        try:
            names = connection.nlst(remote_dir)
        except ftplib.Error as exc:
            raise FTPTransferError(
                f"リモートディレクトリの一覧取得に失敗しました: {remote_dir}"
            ) from exc
        return tuple(names)

    def disconnect(self) -> None:
        """FTPサーバとの接続を切断する。未接続の場合は何もしない。"""
        if self._connection is None:
            return
        try:
            self._connection.quit()
        except (OSError, ftplib.Error):
            self._connection.close()
        finally:
            self._connection = None

    def _require_connection(self) -> ftplib.FTP:
        if self._connection is None:
            raise FTPConnectionError("connect()が呼び出されていません。")
        return self._connection


__all__ = ["StandardFTPClient"]
