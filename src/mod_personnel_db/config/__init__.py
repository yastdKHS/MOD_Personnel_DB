"""設定管理パッケージ（ADR-0028、Phase6 Task14-5）。

環境変数・`.env`ファイル・コンストラクタ引数から読み込む型付き設定
オブジェクト（`AppSettings`、Pydantic Settings実装）を提供する。
`utils/`以外のいかなるパッケージにも依存しない（例外なし、
docs/api/package-design.md#config）。具体的なRepository実装等の
組み立て（配線）は行わない。それは合成ルートである`cli/`の責務である。

`FtpSettings`（`config/ftp.py`、Phase8 Task18-1）は`AppSettings.ftp`が
ネストするFTP接続設定であり、`AppSettings`単体からも到達できるが、
`build_ftp_client()`（`cli/bootstrap.py`）等が型注釈として直接参照できる
よう、本モジュールからも公開する。
"""

from mod_personnel_db.config.ftp import FtpSettings
from mod_personnel_db.config.settings import AppSettings

__all__ = ["AppSettings", "FtpSettings"]
