"""SQLite実装の共有基盤。docs/api/python-contract.md の`SqliteRepositoryBase`に対応する。"""

import sqlite3
from abc import ABC


def connect(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


class SqliteRepositoryBase(ABC):  # noqa: B024 -- 設計文書が指定する共有基盤（抽象メソッドは持たない）
    """8 Repository実装が共有する接続管理。"""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn
