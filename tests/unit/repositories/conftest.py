import sqlite3
from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.models import LayoutId, ParserVersion, ParserVersionId, PdfId, PdfRecord
from mod_personnel_db.repositories.sqlite import apply_schema
from mod_personnel_db.repositories.sqlite._serialization import last_id
from mod_personnel_db.repositories.sqlite.job import SqliteJobRepository
from mod_personnel_db.repositories.sqlite.pdf import SqlitePdfRepository


@pytest.fixture
def conn() -> Generator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def parser_version_id(conn: sqlite3.Connection) -> ParserVersionId:
    repo = SqliteJobRepository(conn)
    version = ParserVersion(
        id=None,
        code_version="v1.0.0",
        knowledge_snapshot_checksum="a" * 64,
        released_at=datetime(2026, 1, 1, tzinfo=UTC),
        notes=None,
    )
    return repo.record_parser_version(version)


@pytest.fixture
def pdf_id(conn: sqlite3.Connection) -> PdfId:
    repo = SqlitePdfRepository(conn)
    pdf = PdfRecord(
        id=None,
        content_hash="b" * 64,
        source_url="https://example.mod.go.jp/appointment.pdf",
        published_date=date(2026, 1, 1),
        fetched_at=datetime(2026, 1, 1, tzinfo=UTC),
        file_path="bb/bb/" + "b" * 64 + ".pdf",
        file_size_bytes=1024,
        status="fetched",
    )
    return repo.add(pdf)


@pytest.fixture
def layout_id(conn: sqlite3.Connection) -> LayoutId:
    # KnowledgeRepository Protocolにはlayouts書き込みメソッドが存在しない
    # （読み取りのみ、docs/api/repositories.mdの既知のギャップ。報告参照）。
    # テストフィクスチャとして直接INSERTする。
    cursor = conn.execute(
        """
        INSERT INTO layouts (era_id, version, manifest_path, manifest_checksum, valid_from, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("reiwa", 1, "layouts/reiwa/manifest.yaml", "c" * 64, "2019-05-01", "active"),
    )
    conn.commit()
    return LayoutId(last_id(cursor))


@pytest.fixture
def layout_era_id(layout_id: LayoutId) -> str:
    # PersonnelSection.layout_id（ADR-0037）はera_id（str）を保持する。
    # layout_idフィクスチャがINSERTしたlayoutsの行と対応するera_idを返す。
    del layout_id
    return "reiwa"
