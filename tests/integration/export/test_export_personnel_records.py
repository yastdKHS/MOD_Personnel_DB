"""ExportServiceのPersonnelRecord公開API（ADR-0016）の結合テスト。

実際のSQLite（`SqliteGoldRepository`、変更なし）へ書き込んだ`GoldRecord`を、
`RepositoryExportService`の新API（`export_all_records()`等、Phase6
Task14-2で追加）経由で読み出し、`GoldRecord`を一切呼び出し元へ返さずに
`PersonnelRecord`へ変換され、JSONシリアライズ可能であることを確認する。
Composition Root（`cli/bootstrap.py`）は経由しない。
"""

import dataclasses
import json
import sqlite3
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mod_personnel_db.export.serialization import to_json_dict
from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.models import (
    CandidateId,
    GoldRecord,
    NormalizedRecord,
    NormalizedValue,
    PersonnelRecord,
    RawRecord,
)
from mod_personnel_db.repositories.sqlite import SqliteGoldRepository, apply_schema, connect


@pytest.fixture
def connection(tmp_path: Path) -> sqlite3.Connection:
    db_path = str(tmp_path / "mod_personnel.sqlite3")
    conn = connect(db_path)
    apply_schema(conn)
    return conn


def _insert_candidate_id(connection: sqlite3.Connection) -> CandidateId:
    """`gold_records.candidate_record_id`のFK制約を満たす最小限の先行データを作成する。"""
    unique = uuid.uuid4().hex
    parser_version_id = connection.execute(
        "INSERT INTO parser_versions (code_version, knowledge_snapshot_checksum) VALUES (?, ?)",
        (f"v1.0.0-test-{unique}", "c" * 64),
    ).lastrowid
    pdf_id = connection.execute(
        "INSERT INTO pdfs (content_hash, source_url, published_date, file_path, file_size_bytes) "
        "VALUES (?, 'https://example.mod.go.jp/x.pdf', '2026-01-01', ?, 1024)",
        (unique, f"bb/bb/{unique}.pdf"),
    ).lastrowid
    layout_id = connection.execute(
        "INSERT INTO layouts (era_id, manifest_path, manifest_checksum, valid_from) "
        "VALUES (?, 'layouts/reiwa/manifest.yaml', ?, '2019-05-01')",
        (f"reiwa-{unique}", "d" * 64),
    ).lastrowid
    section_id = connection.execute(
        "INSERT INTO personnel_sections "
        "(pdf_id, layout_id, parser_version_id, section_index, section_text) "
        "VALUES (?, ?, ?, 0, 'text')",
        (pdf_id, layout_id, parser_version_id),
    ).lastrowid
    candidate_id = connection.execute(
        "INSERT INTO candidate_records "
        "(personnel_section_id, parser_version_id, record_index, raw_fields) "
        'VALUES (?, ?, 0, \'{"rank": "大将?"}\')',
        (section_id, parser_version_id),
    ).lastrowid
    connection.commit()
    assert candidate_id is not None
    return CandidateId(candidate_id)


def _make_normalized_record() -> NormalizedRecord:
    raw = RawRecord(
        section_ref=None,
        layout_id="2026_format_sample",
        record_index=0,
        raw_fields={"rank": "大将?"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _seed_gold_record(connection: sqlite3.Connection, person_key: str) -> None:
    candidate_id = _insert_candidate_id(connection)
    repository = SqliteGoldRepository(connection)
    repository.add_version(
        candidate_id, _make_normalized_record(), person_key, date(2026, 1, 1), "promotion"
    )


def _assert_is_personnel_record_not_gold_record(record: PersonnelRecord) -> None:
    assert isinstance(record, PersonnelRecord)
    assert not isinstance(record, GoldRecord)
    for field in dataclasses.fields(record):
        assert not isinstance(getattr(record, field.name), GoldRecord)


def test_export_all_records_reads_real_sqlite_and_returns_personnel_records(
    connection: sqlite3.Connection,
) -> None:
    _seed_gold_record(connection, "person-integration-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))

    result = service.export_all_records()

    assert len(result) == 1
    _assert_is_personnel_record_not_gold_record(result[0])
    assert result[0].person == NormalizedValue(value="person-integration-1", raw=None)
    assert result[0].confidence.score == 1.0
    assert result[0].provenance.layout_era_id == "2026_format_sample"


def test_export_person_records_reads_real_sqlite(connection: sqlite3.Connection) -> None:
    _seed_gold_record(connection, "person-integration-2")
    _seed_gold_record(connection, "person-integration-3")
    service = RepositoryExportService(SqliteGoldRepository(connection))

    result = service.export_person_records("person-integration-2")

    assert len(result) == 1
    assert result[0].person == NormalizedValue(value="person-integration-2", raw=None)
    _assert_is_personnel_record_not_gold_record(result[0])


def test_export_since_records_reads_real_sqlite(connection: sqlite3.Connection) -> None:
    _seed_gold_record(connection, "person-integration-4")
    service = RepositoryExportService(SqliteGoldRepository(connection))

    result = service.export_since_records(datetime(2099, 1, 1, tzinfo=UTC))

    assert len(result) == 1
    _assert_is_personnel_record_not_gold_record(result[0])


def test_export_all_records_output_is_json_serializable_end_to_end(
    connection: sqlite3.Connection,
) -> None:
    _seed_gold_record(connection, "person-integration-5")
    service = RepositoryExportService(SqliteGoldRepository(connection))

    result = service.export_all_records()
    payload = [to_json_dict(record) for record in result]
    serialized = json.dumps(payload, ensure_ascii=False)
    reloaded = json.loads(serialized)

    assert reloaded == payload
    assert reloaded[0]["person"] == {"value": "person-integration-5", "raw": None}
    assert reloaded[0]["confidence"] == {"score": 1.0, "band": "verified"}
