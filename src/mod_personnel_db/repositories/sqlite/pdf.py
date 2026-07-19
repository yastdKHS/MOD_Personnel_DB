"""PDFRepositoryのSQLite実装。"""

import sqlite3

from mod_personnel_db.models import PdfId, PdfRecord
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import (
    date_to_str,
    dt_to_str,
    last_id,
    str_to_date,
    str_to_dt,
)


def _row_to_record(row: sqlite3.Row) -> PdfRecord:
    return PdfRecord(
        id=PdfId(row["id"]),
        content_hash=row["content_hash"],
        source_url=row["source_url"],
        published_date=str_to_date(row["published_date"]),
        fetched_at=str_to_dt(row["fetched_at"]),
        file_path=row["file_path"],
        file_size_bytes=row["file_size_bytes"],
        status=row["status"],
    )


class SqlitePdfRepository(SqliteRepositoryBase):
    def add(self, pdf: PdfRecord) -> PdfId:
        cursor = self.conn.execute(
            """
            INSERT INTO pdfs (content_hash, source_url, published_date, fetched_at,
                               file_path, file_size_bytes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pdf.content_hash,
                pdf.source_url,
                date_to_str(pdf.published_date),
                dt_to_str(pdf.fetched_at),
                pdf.file_path,
                pdf.file_size_bytes,
                pdf.status,
            ),
        )
        self.conn.commit()
        return PdfId(last_id(cursor))

    def get(self, pdf_id: PdfId) -> PdfRecord | None:
        row = self.conn.execute("SELECT * FROM pdfs WHERE id = ?", (pdf_id,)).fetchone()
        return None if row is None else _row_to_record(row)

    def get_by_hash(self, content_hash: str) -> PdfRecord | None:
        row = self.conn.execute(
            "SELECT * FROM pdfs WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return None if row is None else _row_to_record(row)

    def update_status(self, pdf_id: PdfId, status: str) -> None:
        self.conn.execute(
            "UPDATE pdfs SET status = ?, updated_at = STRFTIME('%Y-%m-%dT%H:%M:%SZ', 'now') "
            "WHERE id = ?",
            (status, pdf_id),
        )
        self.conn.commit()

    def list_by_status(self, status: str) -> tuple[PdfRecord, ...]:
        rows = self.conn.execute(
            "SELECT * FROM pdfs WHERE status = ? ORDER BY id", (status,)
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)
