"""ftp/ パッケージ専用の例外階層。docs/api/python-contract.md の例外設計に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class FTPClientError(MODPersonnelDBError):
    """`ftp/`パッケージの全カスタム例外の基底クラス。"""


class FTPConnectionError(FTPClientError):
    """FTPサーバへの接続確立・認証に失敗した場合、または未接続のまま操作した場合。"""


class FTPTransferError(FTPClientError):
    """アップロード・ダウンロード・リモート一覧取得等のファイル転送操作に失敗した場合。"""


__all__ = ["FTPClientError", "FTPConnectionError", "FTPTransferError"]
