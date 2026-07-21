"""DBスキーマ初期化コマンド。`cli/bootstrap.py`（合成ルート本体）とは別の関心事として分離する。

`repositories.sqlite.apply_schema()`を呼び出す唯一のCLIエントリポイントで
あり、`bootstrap.py`はスキーマ適用を行わない。合成ルートを毎回の実行
（`run_pending`等）で呼び出してもスキーマの再適用（`CREATE TABLE`の重複
実行エラー）が起きないようにするための分離である。
"""

from mod_personnel_db.repositories.sqlite import apply_schema, connect


def initialize_database(db_path: str) -> None:
    """`db_path`のSQLiteファイルへ物理スキーマを一度だけ適用する。"""
    connection = connect(db_path)
    try:
        apply_schema(connection)
    finally:
        connection.close()


__all__ = ["initialize_database"]
