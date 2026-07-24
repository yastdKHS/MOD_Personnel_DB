"""FTP接続設定（Phase8 Task18-1、docs/phase8-integration-design.md#2-ftpsettings導入設計）。

`AppSettings`のネストしたサブ設定として、`ftp/`（`FTPConnectionConfig`）が
必要とする接続情報を型付きで表現する。`ftp/`自身には依存しない
（`config/`は`utils/`以外のいかなるパッケージにも依存しない、
docs/api/package-design.md#config）。`FtpSettings`から`FTPConnectionConfig`
への変換は`cli/bootstrap.py`の`build_ftp_client()`が行う。
"""

from pydantic import BaseModel, SecretStr


class FtpSettings(BaseModel):
    """FTP接続先を表す設定値。`AppSettings.ftp`としてネストされる。

    `password`は`SecretStr`で保持し、ログ・エラーメッセージへの誤出力を防ぐ
    （文字列表現が既定でマスクされる）。
    """

    host: str
    port: int = 21
    username: str = ""
    password: SecretStr = SecretStr("")
    remote_directory: str = "/"
    timeout: float = 30.0


__all__ = ["FtpSettings"]
