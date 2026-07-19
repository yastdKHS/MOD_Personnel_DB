"""ExportRepositoryのSQLite実装。"""

import sqlite3

from mod_personnel_db.models import ExportId, ExportRecord
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import dt_to_str, last_id, str_to_dt


def _row_to_record(row: sqlite3.Row) -> ExportRecord:
    return ExportRecord(
        id=ExportId(row["id"]),
        format=row["format"],
        destination=row["destination"],
        as_of=str_to_dt(row["as_of"]),
        record_count=row["record_count"],
        checksum=row["checksum"],
        status=row["status"],
        created_at=str_to_dt(row["created_at"]),
    )


class SqliteExportRepository(SqliteRepositoryBase):
    def add(self, export: ExportRecord) -> ExportId:
        cursor = self.conn.execute(
            """
            INSERT INTO exports (format, destination, as_of, record_count, checksum, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                export.format,
                export.destination,
                dt_to_str(export.as_of),
                export.record_count,
                export.checksum,
                export.status,
            ),
        )
        self.conn.commit()
        return ExportId(last_id(cursor))

    def get(self, export_id: ExportId) -> ExportRecord | None:
        row = self.conn.execute("SELECT * FROM exports WHERE id = ?", (export_id,)).fetchone()
        return None if row is None else _row_to_record(row)

    def list_recent(self, limit: int = 10) -> tuple[ExportRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM exports ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def get_latest(self, format: str) -> ExportRecord | None:
        row = self.conn.execute(
            "SELECT * FROM exports WHERE format = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (format,),
        ).fetchone()
        return None if row is None else _row_to_record(row)
