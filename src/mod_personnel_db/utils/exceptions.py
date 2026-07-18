"""例外階層。docs/api/python-contract.md の例外設計に対応する。"""


class MODPersonnelDBError(Exception):
    """本プロジェクトの全カスタム例外の基底クラス。"""


class RepositoryError(MODPersonnelDBError):
    """Repository層での永続化エラー（接続断・整合性制約違反等）の基底クラス。"""


class KnowledgeLoadError(MODPersonnelDBError):
    """knowledge/ のファイル読み込み・スキーマ検証エラー。"""


class ValidationBlockedError(MODPersonnelDBError):
    """ValidationRuleSetが取得できない等、検証自体を実行できない場合。"""
