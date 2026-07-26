"""FTPClient契約（Protocol）と実装。Phase7 Task16-1に対応する。

docs/api/interfaces.md#ftpservice が定める`FTPService`Protocol
（`upload`/`download`/`list_remote`）に、docs/api/package-design.md の
`ftp/`節（Phase7 Task16-0で設計確定）が要求する明示的な`connect()`/
`disconnect()`ライフサイクルを加えたものが本パッケージの`FTPClient`
Protocolである。両者はメソッド名の一部が重複するが別の型として定義しており、
命名の統合は将来のADRに委ねる（`review/`・`export/`が実装済みの狭い契約と
`docs/api/`が描く広い契約を別の契約として扱っている既存の整理に準じる）。

`rename()`はTask19-5で追加した拡張であり、`docs/api/interfaces.md#ftpservice`
が定める`FTPService`契約には含まれない（`upload()`のatomic化・リモート
バックアップ生成のために`StandardFTPClient.upload()`内部が利用する）。
`delete()`はTask19-17で追加した拡張であり、同じく`FTPService`契約には
含まれない（ATSON FTPd v0.9.14.9が既存ファイルへの`RNTO`を`553 already
exist`で拒否するため、`upload()`が既存の`.bak`を`rename()`前に削除する
用途で利用する）。

バイト列・パス文字列のみを扱うプロトコル層に徹し、ドメインモデル（`models/`）・
`repositories/`（抽象含む）のいずれにも依存しない（依存先は`utils/`のみ）。
接続情報（`FTPConnectionConfig`）は呼び出し側からプレーンな引数として渡され、
本パッケージは`config/`を一切参照しない。

具象実装（`StandardFTPClient`、`ftplib`ベース）・テスト用モック実装
（`InMemoryFTPClient`）はそれぞれ`ftp.client`・`ftp.mock`から提供する。
"""

from typing import Protocol

from mod_personnel_db.ftp.client import StandardFTPClient
from mod_personnel_db.ftp.config import FTPConnectionConfig
from mod_personnel_db.ftp.exceptions import FTPClientError, FTPConnectionError, FTPTransferError
from mod_personnel_db.ftp.mock import InMemoryFTPClient


class FTPClient(Protocol):
    """FTP経由でのファイル転送を提供するプロトコル層（バイト列・パス文字列のみを扱う）。"""

    def connect(self) -> None:
        """FTPサーバへ接続する。"""
        ...

    def upload(self, local_path: str, remote_path: str) -> None:
        """`local_path`のファイルを`remote_path`へアップロードする。"""
        ...

    def download(self, remote_path: str, local_path: str) -> None:
        """`remote_path`のファイルを`local_path`へダウンロードする。"""
        ...

    def list_remote(self, remote_dir: str) -> tuple[str, ...]:
        """`remote_dir`配下のエントリ名一覧を返す。"""
        ...

    def rename(self, from_name: str, to_name: str) -> None:
        """`from_name`を`to_name`へリネームする（Task19-5）。"""
        ...

    def delete(self, remote_path: str) -> None:
        """`remote_path`を削除する（Task19-17）。"""
        ...

    def disconnect(self) -> None:
        """FTPサーバとの接続を切断する。"""
        ...


__all__ = [
    "FTPClient",
    "FTPClientError",
    "FTPConnectionConfig",
    "FTPConnectionError",
    "FTPTransferError",
    "InMemoryFTPClient",
    "StandardFTPClient",
]
