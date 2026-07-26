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
        """FTPサーバへ接続しログインする。接続済みの場合は何もしない。

        `config.remote_directory`が空文字列でない場合、ログイン直後に
        当該ディレクトリへ`cwd()`する。以降の`upload()`/`download()`/
        `list_remote()`に渡す`remote_path`は、このディレクトリからの
        相対パスとして解決される。`remote_directory`が空文字列（既定）の
        場合は`cwd()`を呼び出さず、従来どおりログイン直後のディレクトリを
        維持する（後方互換）。
        """
        if self._connection is not None:
            return
        connection = ftplib.FTP()
        try:
            connection.connect(self._config.host, self._config.port, timeout=self._config.timeout)
            connection.login(self._config.username, self._config.password)
            connection.set_pasv(self._config.passive)
            if self._config.remote_directory:
                connection.cwd(self._config.remote_directory)
        except (OSError, ftplib.Error) as exc:
            raise FTPConnectionError(
                f"FTPサーバへの接続に失敗しました: {self._config.host}:{self._config.port}"
            ) from exc
        self._connection = connection

    def upload(self, local_path: str, remote_path: str) -> None:
        """`local_path`のファイルをバイナリモードで`remote_path`へアップロードする。

        転送途中の失敗で`remote_path`（正式ファイル）を破損・消失させないよう、
        一時ファイル名へSTORしてから正式名称へrenameするatomicな手順を踏む
        （Task19-5）。既存の`remote_path`が存在する場合は、最終renameの直前に
        バックアップ名（`remote_path + ".bak"`）へ退避する。STOR失敗時・
        バックアップrename失敗時のいずれも`remote_path`は変更されない。
        """
        connection = self._require_connection()
        temp_remote_path = f"{remote_path}.uploading"
        try:
            with Path(local_path).open("rb") as source:
                connection.storbinary(f"STOR {temp_remote_path}", source)
        except (OSError, ftplib.Error) as exc:
            raise FTPTransferError(
                f"アップロードに失敗しました: {local_path} -> {remote_path}"
            ) from exc
        if self._remote_file_exists(remote_path):
            self.rename(remote_path, f"{remote_path}.bak")
        self.rename(temp_remote_path, remote_path)

    def rename(self, from_name: str, to_name: str) -> None:
        """`from_name`を`to_name`へリネームする（`RNFR`/`RNTO`、Task19-5）。"""
        connection = self._require_connection()
        try:
            connection.rename(from_name, to_name)
        except (OSError, ftplib.Error) as exc:
            raise FTPTransferError(f"リネームに失敗しました: {from_name} -> {to_name}") from exc

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

    def _remote_file_exists(self, remote_path: str) -> bool:
        """`remote_path`が既に存在するかを`SIZE`で確認する（backup要否判定用）。

        Task19-13の実FTP検証により、ATSON FTPd v0.9.14.9では単一ファイルの
        存在確認に`NLST`を用いると`TYPE A`への切り替えが発生し、後続の`PASV`で
        `426 ASCII Transfer aborted`となり既存ファイルでも存在確認に失敗する
        ことが判明した。`SIZE`は同サーバで正しく動作する（存在時はサイズを
        返し、不存在時は`550`を返す）ことを実FTP検証済みのため、Task19-15で
        `SIZE`方式へ変更した。サイズの値自体は判定に用いず、`SIZE`が成功した
        かどうかのみを見る（0byteファイルも存在扱いとする）。
        """
        connection = self._require_connection()
        try:
            connection.size(remote_path)
        except ftplib.error_perm:
            return False
        except (OSError, ftplib.Error) as exc:
            raise FTPTransferError(f"存在確認に失敗しました: {remote_path}") from exc
        return True


__all__ = ["StandardFTPClient"]
