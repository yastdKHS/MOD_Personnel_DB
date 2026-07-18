import sqlite3
from datetime import UTC, datetime

from mod_personnel_db.models import ExportId, ExportRecord
from mod_personnel_db.models.export import ExportFormat
from mod_personnel_db.repositories.sqlite.export import SqliteExportRepository


def _make_export(fmt: ExportFormat = "json", as_of: datetime | None = None) -> ExportRecord:
    return ExportRecord(
        id=None,
        format=fmt,
        destination="ftp://example/export.json",
        as_of=as_of or datetime(2026, 1, 1, tzinfo=UTC),
        record_count=100,
        checksum="sha256:" + "a" * 64,
        status="completed",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_add_and_get(conn: sqlite3.Connection) -> None:
    repo = SqliteExportRepository(conn)
    export_id = repo.add(_make_export())

    fetched = repo.get(export_id)

    assert fetched is not None
    assert fetched.format == "json"
    assert fetched.record_count == 100


def test_get_missing_returns_none(conn: sqlite3.Connection) -> None:
    repo = SqliteExportRepository(conn)
    assert repo.get(ExportId(999)) is None


def test_list_recent_orders_newest_first(conn: sqlite3.Connection) -> None:
    repo = SqliteExportRepository(conn)
    first = repo.add(_make_export(as_of=datetime(2026, 1, 1, tzinfo=UTC)))
    second = repo.add(_make_export(as_of=datetime(2026, 2, 1, tzinfo=UTC)))

    recent = repo.list_recent(limit=10)

    assert [r.id for r in recent] == [second, first]


def test_list_recent_respects_limit(conn: sqlite3.Connection) -> None:
    repo = SqliteExportRepository(conn)
    for _ in range(3):
        repo.add(_make_export())

    assert len(repo.list_recent(limit=2)) == 2


def test_get_latest_by_format(conn: sqlite3.Connection) -> None:
    repo = SqliteExportRepository(conn)
    repo.add(_make_export(fmt="csv"))
    json_id = repo.add(_make_export(fmt="json"))

    latest_json = repo.get_latest("json")
    latest_parquet = repo.get_latest("parquet")

    assert latest_json is not None
    assert latest_json.id == json_id
    assert latest_parquet is None
