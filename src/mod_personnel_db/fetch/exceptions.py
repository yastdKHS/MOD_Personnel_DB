"""fetch/ パッケージ専用の例外階層。docs/api/python-contract.md の例外設計に対応する。"""

from mod_personnel_db.utils.exceptions import MODPersonnelDBError


class FetchError(MODPersonnelDBError):
    """`fetch/`パッケージの全カスタム例外の基底クラス。"""


class FetchValidationError(FetchError):
    """`FetchRequest`の内容が不正な場合（空URL・非対応スキーム等）。"""


class FetchTimeoutError(FetchError):
    """取得がタイムアウトした場合。"""


class FetchNetworkError(FetchError):
    """タイムアウト以外のネットワークエラー（DNS解決失敗・接続拒否等）。"""


class FetchStatusError(FetchError):
    """HTTPステータスコードが期待値と一致しない場合。"""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class FetchContentTypeError(FetchError):
    """Content-Typeが期待値と一致しない場合。"""

    def __init__(self, message: str, *, content_type: str | None) -> None:
        super().__init__(message)
        self.content_type = content_type


__all__ = [
    "FetchContentTypeError",
    "FetchError",
    "FetchNetworkError",
    "FetchStatusError",
    "FetchTimeoutError",
    "FetchValidationError",
]
