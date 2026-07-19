import sqlite3
from datetime import UTC, datetime

from mod_personnel_db.models import Job, JobId, ParserVersion
from mod_personnel_db.models.job import JobType
from mod_personnel_db.repositories.sqlite.job import SqliteJobRepository


def _make_job(job_type: JobType = "core_pipeline") -> Job:
    return Job(
        id=None,
        job_type=job_type,
        pdf_id=None,
        parser_version_id=None,
        status="running",
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at=None,
        processed_count=0,
        failed_count=0,
        error_summary=None,
    )


def test_add_and_get_job(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    job_id = repo.add(_make_job())

    fetched = repo.get(job_id)

    assert fetched is not None
    assert fetched.status == "running"
    assert fetched.finished_at is None


def test_get_missing_job_returns_none(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    assert repo.get(JobId(999)) is None


def test_update_status_sets_finished_at(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    job_id = repo.add(_make_job())

    repo.update_status(job_id, "succeeded", processed_count=10, failed_count=1)

    updated = repo.get(job_id)
    assert updated is not None
    assert updated.status == "succeeded"
    assert updated.processed_count == 10
    assert updated.failed_count == 1
    assert updated.finished_at is not None


def test_update_status_running_keeps_finished_at_none(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    job_id = repo.add(_make_job())

    repo.update_status(job_id, "running", processed_count=1, failed_count=0)
    fetched = repo.get(job_id)

    assert fetched is not None
    assert fetched.finished_at is None


def test_list_running(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    running_id = repo.add(_make_job())
    other_id = repo.add(_make_job(job_type="fetch"))
    repo.update_status(other_id, "succeeded", processed_count=1, failed_count=0)

    running = repo.list_running()

    assert [j.id for j in running] == [running_id]


def test_record_and_get_parser_version(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    version = ParserVersion(
        id=None,
        code_version="v1.2.3",
        knowledge_snapshot_checksum="a" * 64,
        released_at=datetime(2026, 2, 1, tzinfo=UTC),
        notes="initial release",
    )

    version_id = repo.record_parser_version(version)

    by_code = repo.get_parser_version("v1.2.3")
    latest = repo.get_latest_parser_version()
    missing = repo.get_parser_version("v9.9.9")

    assert by_code is not None
    assert by_code.id == version_id
    assert latest is not None
    assert latest.code_version == "v1.2.3"
    assert missing is None


def test_get_latest_parser_version_picks_most_recent(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    repo.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v1.0.0",
            knowledge_snapshot_checksum="a" * 64,
            released_at=datetime(2026, 1, 1, tzinfo=UTC),
            notes=None,
        )
    )
    repo.record_parser_version(
        ParserVersion(
            id=None,
            code_version="v2.0.0",
            knowledge_snapshot_checksum="b" * 64,
            released_at=datetime(2026, 3, 1, tzinfo=UTC),
            notes=None,
        )
    )

    latest = repo.get_latest_parser_version()

    assert latest is not None
    assert latest.code_version == "v2.0.0"


def test_get_latest_parser_version_empty(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    assert repo.get_latest_parser_version() is None


def test_duplicate_code_version_rejected(conn: sqlite3.Connection) -> None:
    repo = SqliteJobRepository(conn)
    version = ParserVersion(
        id=None,
        code_version="v1.0.0",
        knowledge_snapshot_checksum="a" * 64,
        released_at=datetime(2026, 1, 1, tzinfo=UTC),
        notes=None,
    )
    repo.record_parser_version(version)

    try:
        repo.record_parser_version(version)
    except sqlite3.IntegrityError:
        return
    raise AssertionError("expected sqlite3.IntegrityError for duplicate code_version")
