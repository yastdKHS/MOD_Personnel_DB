"""KnowledgeRepositoryのSQLite実装。knowledge_items と layouts を担当する。"""

import hashlib
import sqlite3
from datetime import date

from mod_personnel_db.models import KnowledgeItem, KnowledgeItemId, Layout, LayoutId
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import date_to_str, str_to_date


def _content_checksum(item: KnowledgeItem) -> str:
    # KnowledgeItemモデルはsource_checksumを持たない（docs/api/models.mdとdocs/database/schema.md
    # の差分。DB列source_checksumはNOT NULLのため、内容から導出して埋める）。
    payload = f"{item.category}:{item.source_file}:{item.item_key}:{item.canonical_value}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _row_to_item(row: sqlite3.Row) -> KnowledgeItem:
    return KnowledgeItem(
        id=KnowledgeItemId(row["id"]),
        category=row["category"],
        source_file=row["source_file"],
        item_key=row["item_key"],
        canonical_value=row["canonical_value"],
        effective_from=None
        if row["effective_from"] is None
        else str_to_date(row["effective_from"]),
        effective_to=None if row["effective_to"] is None else str_to_date(row["effective_to"]),
        provenance_source=row["provenance_source"],
        version=row["version"],
    )


def _row_to_layout(row: sqlite3.Row) -> Layout:
    return Layout(
        id=LayoutId(row["id"]),
        era_id=row["era_id"],
        version=row["version"],
        manifest_path=row["manifest_path"],
        manifest_checksum=row["manifest_checksum"],
        valid_from=str_to_date(row["valid_from"]),
        valid_to=None if row["valid_to"] is None else str_to_date(row["valid_to"]),
        status=row["status"],
    )


class SqliteKnowledgeRepository(SqliteRepositoryBase):
    def upsert_item(self, item: KnowledgeItem) -> None:
        current = self.conn.execute(
            "SELECT * FROM knowledge_items WHERE category = ? AND item_key = ? "
            "AND effective_to IS NULL",
            (item.category, item.item_key),
        ).fetchone()

        if current is not None:
            unchanged = (
                current["canonical_value"] == item.canonical_value
                and current["source_file"] == item.source_file
            )
            if unchanged:
                return
            close_from = date_to_str(item.effective_from or date.today())
            self.conn.execute(
                "UPDATE knowledge_items SET effective_to = ? WHERE id = ?",
                (close_from, current["id"]),
            )

        self.conn.execute(
            """
            INSERT INTO knowledge_items
                (category, source_file, item_key, canonical_value, effective_from, effective_to,
                 source_checksum, provenance_source, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.category,
                item.source_file,
                item.item_key,
                item.canonical_value,
                None if item.effective_from is None else date_to_str(item.effective_from),
                None if item.effective_to is None else date_to_str(item.effective_to),
                _content_checksum(item),
                item.provenance_source,
                item.version,
            ),
        )
        self.conn.commit()

    def get_item(
        self, category: str, item_key: str, as_of: date | None = None
    ) -> KnowledgeItem | None:
        if as_of is None:
            row = self.conn.execute(
                "SELECT * FROM knowledge_items WHERE category = ? AND item_key = ? "
                "AND effective_to IS NULL",
                (category, item_key),
            ).fetchone()
        else:
            as_of_str = date_to_str(as_of)
            row = self.conn.execute(
                "SELECT * FROM knowledge_items WHERE category = ? AND item_key = ? "
                "AND (effective_from IS NULL OR effective_from <= ?) "
                "AND (effective_to IS NULL OR effective_to > ?) "
                "ORDER BY effective_from DESC LIMIT 1",
                (category, item_key, as_of_str, as_of_str),
            ).fetchone()
        return None if row is None else _row_to_item(row)

    def list_items(self, category: str) -> tuple[KnowledgeItem, ...]:
        rows = self.conn.execute(
            "SELECT * FROM knowledge_items WHERE category = ? ORDER BY item_key, effective_from",
            (category,),
        ).fetchall()
        return tuple(_row_to_item(row) for row in rows)

    def get_layout(self, era_id: str, version: int | None = None) -> Layout | None:
        if version is None:
            row = self.conn.execute(
                "SELECT * FROM layouts WHERE era_id = ? ORDER BY version DESC LIMIT 1",
                (era_id,),
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT * FROM layouts WHERE era_id = ? AND version = ?",
                (era_id, version),
            ).fetchone()
        return None if row is None else _row_to_layout(row)

    def list_active_layouts(self, as_of: date | None = None) -> tuple[Layout, ...]:
        if as_of is None:
            rows = self.conn.execute(
                "SELECT * FROM layouts WHERE status = 'active' ORDER BY era_id, version"
            ).fetchall()
        else:
            as_of_str = date_to_str(as_of)
            rows = self.conn.execute(
                "SELECT * FROM layouts WHERE valid_from <= ? "
                "AND (valid_to IS NULL OR valid_to > ?) ORDER BY era_id, version",
                (as_of_str, as_of_str),
            ).fetchall()
        return tuple(_row_to_layout(row) for row in rows)
