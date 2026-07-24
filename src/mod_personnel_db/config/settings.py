"""`AppSettings`: Pydantic Settingsによる型付き設定オブジェクト（ADR-0028）。

環境変数（`MOD_PERSONNEL_DB_`プレフィックス）・`.env`ファイル・コンストラクタ
引数から設定値を読み込む。読み込み優先順位はpydantic-settingsの既定動作に
従う（コンストラクタ引数 > 環境変数 > `.env`ファイル > フィールドの
デフォルト値）。

設定項目は、置き換え対象である`cli/bootstrap.py`の旧`CompositionSettings`
（`db_path`/`knowledge_root`/`layouts_root`/`parser_code_version`の4
フィールド）と等価になるよう定義する（Phase6 Task14-5）。Phase8 Task18-1で
`ftp`（`FtpSettings`、`config/ftp.py`）をネストしたサブ設定として追加した
（docs/phase8-integration-design.md#2-ftpsettings導入設計）。`docs/configuration.md`
が設計する`DatabaseSettings`・`Environment`は引き続き本Taskの対象外
（未実装のまま）とする。

`env_nested_delimiter="__"`により、`MOD_PERSONNEL_DB_FTP__HOST`等の環境変数が
`ftp.host`へマッピングされる。`ftp`関連の環境変数が一切指定されない場合、
`ftp`フィールドは`None`のままとなり（既存4フィールドのみのCompositionSettings
と完全に等価な状態）、既存の呼び出し元・テストへの後方互換性を維持する。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from mod_personnel_db.config.ftp import FtpSettings


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
        env_nested_delimiter="__",
        extra="ignore",
        frozen=True,
    )

    db_path: str
    knowledge_root: Path
    layouts_root: Path
    parser_code_version: str = "v1.0.0"
    ftp: FtpSettings | None = None


__all__ = ["AppSettings"]
