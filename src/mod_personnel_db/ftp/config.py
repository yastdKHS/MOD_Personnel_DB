"""FTP接続設定。docs/api/package-design.md のftp/節（Phase7 Task16-0で設計確定）に対応する。

`ftp/`は`config/`に直接依存しない。接続先ホスト・ポート・ユーザー名・
パスワードは、呼び出し側（`fetch/`または`services/`、将来実装）が
プレーンな引数として本モデルへ渡す。秘匿情報の読み込み・解決自体は
合成ルート（`cli/`、将来は`services/`が仲介する場合もこれに準じる）の
責務であり、`ftp/`自身が環境変数や設定ファイルを読みに行くことはない。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FTPConnectionConfig:
    """FTP接続先を表す不変の値オブジェクト。ドメインモデル（`models/`）ではない。

    `remote_directory`は空文字列（既定）の場合、接続後の`cwd()`を行わない
    （後方互換: 既存の呼び出し元は挙動を変えずにそのまま動作する）。
    """

    host: str
    port: int = 21
    username: str = ""
    password: str = ""
    timeout: float = 30.0
    passive: bool = True
    remote_directory: str = ""


__all__ = ["FTPConnectionConfig"]
