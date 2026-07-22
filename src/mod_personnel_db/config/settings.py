"""`AppSettings`: Pydantic Settingsによる型付き設定オブジェクト（ADR-0028）。

環境変数（`MOD_PERSONNEL_DB_`プレフィックス）・`.env`ファイル・コンストラクタ
引数から設定値を読み込む。読み込み優先順位はpydantic-settingsの既定動作に
従う（コンストラクタ引数 > 環境変数 > `.env`ファイル > フィールドの
デフォルト値）。

設定項目は、置き換え対象である`cli/bootstrap.py`の旧`CompositionSettings`
（`db_path`/`knowledge_root`/`layouts_root`/`parser_code_version`の4
フィールド）と等価になるよう定義する（Phase6 Task14-5）。`docs/configuration.md`
が設計する`DatabaseSettings`/`FtpSettings`等のネスト構造・`Environment`・
`SecretStr`は本Taskの対象外（未実装のまま）とし、既存`CompositionSettings`と
の等価性のみを満たす最小構成にとどめる。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """アプリケーション全体の設定値（ADR-0028）。

    合成ルート（`cli/bootstrap.py`）のみがこのクラスを生成する
    （docs/api/dependency-rule.md#合成ルートcomposition-root）。読み込み後の
    インスタンスは不変（`frozen=True`）として扱う（docs/configuration.md
    #pydantic-settings）。
    """

    model_config = SettingsConfigDict(
        env_prefix="MOD_PERSONNEL_DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    db_path: str
    knowledge_root: Path
    layouts_root: Path
    parser_code_version: str = "v1.0.0"


__all__ = ["AppSettings"]
