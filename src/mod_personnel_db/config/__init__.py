"""設定管理パッケージ（ADR-0028、Phase6 Task14-5）。

環境変数・`.env`ファイル・コンストラクタ引数から読み込む型付き設定
オブジェクト（`AppSettings`、Pydantic Settings実装）を提供する。
`utils/`以外のいかなるパッケージにも依存しない（例外なし、
docs/api/package-design.md#config）。具体的なRepository実装等の
組み立て（配線）は行わない。それは合成ルートである`cli/`の責務である。
"""

from mod_personnel_db.config.settings import AppSettings

__all__ = ["AppSettings"]
