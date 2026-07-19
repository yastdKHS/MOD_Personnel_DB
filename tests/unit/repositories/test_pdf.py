import sqlite3
from datetime import UTC, date, datetime

from mod_personnel_db.models import PdfId, PdfRecord
from mod_personnel_db.repositories.sqlite.pdf import SqlitePdfRepository


def _make_pdf(content_hash: str = "a" * 64) -> PdfRecord:
    return PdfRecord(
        id=None,
        content_hash=content_hash,
        source_url="https://example.mod.go.jp/x.pdf",
        published_date=date(2026, 1, 1),
        fetched_at=datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC),
        file_path="aa/aa/" + content_hash + ".pdf",
        file_size_bytes=2048,
        status="fetched",
    )


def test_add_and_get(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    pdf_id = repo.add(_make_pdf())

    fetched = repo.get(pdf_id)

    assert fetched is not None
    assert fetched.id == pdf_id
    assert fetched.content_hash == "a" * 64
    assert fetched.status == "fetched"


def test_get_missing_returns_none(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    pdf_id = repo.add(_make_pdf())

    assert repo.get(pdf_id) is not None
    assert repo.get(PdfId(999)) is None


def test_get_by_hash(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    pdf_id = repo.add(_make_pdf(content_hash="d" * 64))

    found = repo.get_by_hash("d" * 64)
    missing = repo.get_by_hash("e" * 64)

    assert found is not None
    assert found.id == pdf_id
    assert missing is None


def test_update_status(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    pdf_id = repo.add(_make_pdf())

    repo.update_status(pdf_id, "validated")
    fetched = repo.get(pdf_id)

    assert fetched is not None
    assert fetched.status == "validated"


def test_list_by_status(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    repo.add(_make_pdf(content_hash="1" * 64))
    second = repo.add(_make_pdf(content_hash="2" * 64))
    repo.update_status(second, "failed")

    fetched = repo.list_by_status("fetched")
    failed = repo.list_by_status("failed")

    assert len(fetched) == 1
    assert len(failed) == 1
    assert failed[0].id == second


def test_duplicate_content_hash_rejected(conn: sqlite3.Connection) -> None:
    repo = SqlitePdfRepository(conn)
    repo.add(_make_pdf(content_hash="f" * 64))

    try:
        repo.add(_make_pdf(content_hash="f" * 64))
    except sqlite3.IntegrityError:
        return
    raise AssertionError("expected sqlite3.IntegrityError for duplicate content_hash")
