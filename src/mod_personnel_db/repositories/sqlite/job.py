"""JobRepositoryのSQLite実装。jobs と parser_versions を担当する。"""

import sqlite3
from datetime import UTC, datetime

from mod_personnel_db.models import Job, JobId, ParserVersion, ParserVersionId, PdfId
from mod_personnel_db.repositories.sqlite._base import SqliteRepositoryBase
from mod_personnel_db.repositories.sqlite._serialization import dt_to_str, last_id, str_to_dt


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=JobId(row["id"]),
        job_type=row["job_type"],
        pdf_id=None if row["pdf_id"] is None else PdfId(row["pdf_id"]),
        parser_version_id=(
            None if row["parser_version_id"] is None else ParserVersionId(row["parser_version_id"])
        ),
        status=row["status"],
        started_at=str_to_dt(row["started_at"]),
        finished_at=None if row["finished_at"] is None else str_to_dt(row["finished_at"]),
        processed_count=row["processed_count"],
        failed_count=row["failed_count"],
        error_summary=row["error_summary"],
    )


def _row_to_parser_version(row: sqlite3.Row) -> ParserVersion:
    return ParserVersion(
        id=ParserVersionId(row["id"]),
        code_version=row["code_version"],
        knowledge_snapshot_checksum=row["knowledge_snapshot_checksum"],
        released_at=str_to_dt(row["released_at"]),
        notes=row["notes"],
    )


class SqliteJobRepository(SqliteRepositoryBase):
    def add(self, job: Job) -> JobId:
        cursor = self.conn.execute(
            """
            INSERT INTO jobs (job_type, pdf_id, parser_version_id, status, started_at,
                               finished_at, processed_count, failed_count, error_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.job_type,
                job.pdf_id,
                job.parser_version_id,
                job.status,
                dt_to_str(job.started_at),
                None if job.finished_at is None else dt_to_str(job.finished_at),
                job.processed_count,
                job.failed_count,
                job.error_summary,
            ),
        )
        self.conn.commit()
        return JobId(last_id(cursor))

    def update_status(
        self, job_id: JobId, status: str, processed_count: int, failed_count: int
    ) -> None:
        finished_at = None if status == "running" else dt_to_str(datetime.now(UTC))
        self.conn.execute(
            "UPDATE jobs SET status = ?, processed_count = ?, failed_count = ?, "
            "finished_at = COALESCE(?, finished_at) WHERE id = ?",
            (status, processed_count, failed_count, finished_at, job_id),
        )
        self.conn.commit()

    def get(self, job_id: JobId) -> Job | None:
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return None if row is None else _row_to_job(row)

    def list_running(self) -> tuple[Job, ...]:
        rows = self.conn.execute(
            "SELECT * FROM jobs WHERE status = 'running' ORDER BY id"
        ).fetchall()
        return tuple(_row_to_job(row) for row in rows)

    def record_parser_version(self, version: ParserVersion) -> ParserVersionId:
        cursor = self.conn.execute(
            """
            INSERT INTO parser_versions
                (code_version, knowledge_snapshot_checksum, released_at, notes)
            VALUES (?, ?, ?, ?)
            """,
            (
                version.code_version,
                version.knowledge_snapshot_checksum,
                dt_to_str(version.released_at),
                version.notes,
            ),
        )
        self.conn.commit()
        return ParserVersionId(last_id(cursor))

    def get_parser_version(self, code_version: str) -> ParserVersion | None:
        row = self.conn.execute(
            "SELECT * FROM parser_versions WHERE code_version = ?", (code_version,)
        ).fetchone()
        return None if row is None else _row_to_parser_version(row)

    def get_latest_parser_version(self) -> ParserVersion | None:
        row = self.conn.execute(
            "SELECT * FROM parser_versions ORDER BY released_at DESC, id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else _row_to_parser_version(row)
