"""tools/db_audit.py（Task34 Step3）のテスト。

tools/はsrc/のパッケージではないため、importlibでファイルパスから直接
モジュールをロードする（scripts/README.mdと同じ位置づけの運用補助ツール、
tools/db_audit.pyのdocstring参照）。
"""

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest

from mod_personnel_db.repositories.sqlite import apply_schema

_MODULE_PATH = Path(__file__).resolve().parents[3] / "tools" / "db_audit.py"
_SPEC = importlib.util.spec_from_file_location("db_audit", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
db_audit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(db_audit)


@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    apply_schema(connection)
    return connection


def _insert_pdf(conn: sqlite3.Connection, content_hash: str) -> int:
    cursor = conn.execute(
        "INSERT INTO pdfs (content_hash, source_url, published_date, file_path, file_size_bytes) "
        "VALUES (?, 'https://example.test/x.pdf', '2026-01-01', '/tmp/x.pdf', 1)",
        (content_hash,),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _insert_layout(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "INSERT INTO layouts (era_id, manifest_path, manifest_checksum, valid_from) "
        "VALUES ('reiwa', 'layouts/reiwa/manifest.yaml', 'x', '2019-05-01')"
    )
    conn.commit()
    return int(cursor.lastrowid)


def _insert_parser_version(conn: sqlite3.Connection, code_version: str) -> int:
    cursor = conn.execute(
        "INSERT INTO parser_versions (code_version, knowledge_snapshot_checksum) VALUES (?, 'x')",
        (code_version,),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _insert_section(
    conn: sqlite3.Connection, pdf_id: int, layout_id: int, parser_version_id: int, status: str
) -> int:
    cursor = conn.execute(
        "INSERT INTO personnel_sections "
        "(pdf_id, layout_id, parser_version_id, section_index, section_text, status) "
        "VALUES (?, ?, ?, 0, 'text', ?)",
        (pdf_id, layout_id, parser_version_id, status),
    )
    conn.commit()
    return int(cursor.lastrowid)


def test_clean_db_reports_no_findings(conn: sqlite3.Connection) -> None:
    results = db_audit.run_audit(conn, db_audit.build_checks(24))
    assert all(not result.rows for result in results)
    assert db_audit.determine_exit_code(results) == 0


def test_detects_duplicate_parsed_sections(conn: sqlite3.Connection) -> None:
    pdf_id = _insert_pdf(conn, "hash-1")
    layout_id = _insert_layout(conn)
    v1 = _insert_parser_version(conn, "v1.0.0")
    v2 = _insert_parser_version(conn, "v2.0.0")
    _insert_section(conn, pdf_id, layout_id, v1, "parsed")
    _insert_section(conn, pdf_id, layout_id, v2, "parsed")

    results = db_audit.run_audit(conn, db_audit.build_checks(24))

    q1 = next(result for result in results if result.check.check_id == "Q1")
    assert len(q1.rows) == 1
    assert q1.check.severity == "error"
    assert db_audit.determine_exit_code(results) == 2


def test_detects_stale_running_job(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO jobs (job_type, status, started_at) "
        "VALUES ('fetch', 'running', '2000-01-01T00:00:00Z')"
    )
    conn.commit()

    results = db_audit.run_audit(conn, db_audit.build_checks(24))

    q8 = next(result for result in results if result.check.check_id == "Q8")
    assert len(q8.rows) == 1
    assert q8.check.severity == "warning"
    assert db_audit.determine_exit_code(results) == 1


def test_format_json_reports_only_findings(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO jobs (job_type, status, started_at) "
        "VALUES ('fetch', 'running', '2000-01-01T00:00:00Z')"
    )
    conn.commit()

    results = db_audit.run_audit(conn, db_audit.build_checks(24))
    payload = json.loads(db_audit.format_json(results))

    assert payload["exit_code"] == 1
    assert len(payload["checks"]) == 1
    assert payload["checks"][0]["id"] == "Q8"


def test_open_readonly_connection_rejects_write(tmp_path: Path) -> None:
    db_path = tmp_path / "readonly_test.db"
    setup_conn = sqlite3.connect(str(db_path))
    apply_schema(setup_conn)
    setup_conn.close()

    ro_conn = db_audit.open_readonly_connection(str(db_path))
    try:
        with pytest.raises(sqlite3.OperationalError):
            ro_conn.execute(
                "INSERT INTO pdfs (content_hash, source_url, published_date, file_path, "
                "file_size_bytes) VALUES ('h', 'u', '2026-01-01', '/tmp/x', 1)"
            )
    finally:
        ro_conn.close()


def test_open_readonly_connection_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        db_audit.open_readonly_connection(str(tmp_path / "missing.db"))
