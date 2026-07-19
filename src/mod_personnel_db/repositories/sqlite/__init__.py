"""Repository ProtocolのSQLite実装（Infrastructure層）。

このパッケージ配下だけがsqlite3に依存する
（docs/implementation.md#no-sqlite-dependency-outside-infrastructure）。
"""

from mod_personnel_db.repositories.sqlite._base import connect
from mod_personnel_db.repositories.sqlite._schema import apply_schema
from mod_personnel_db.repositories.sqlite.candidate import SqliteCandidateRepository
from mod_personnel_db.repositories.sqlite.export import SqliteExportRepository
from mod_personnel_db.repositories.sqlite.gold import SqliteGoldRepository
from mod_personnel_db.repositories.sqlite.job import SqliteJobRepository
from mod_personnel_db.repositories.sqlite.knowledge import SqliteKnowledgeRepository
from mod_personnel_db.repositories.sqlite.pdf import SqlitePdfRepository
from mod_personnel_db.repositories.sqlite.review import SqliteReviewRepository

__all__ = [
    "SqliteCandidateRepository",
    "SqliteExportRepository",
    "SqliteGoldRepository",
    "SqliteJobRepository",
    "SqliteKnowledgeRepository",
    "SqlitePdfRepository",
    "SqliteReviewRepository",
    "apply_schema",
    "connect",
]
