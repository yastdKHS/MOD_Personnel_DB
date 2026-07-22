"""ExportServiceの完全性保証・監査情報API（ADR-0029）の結合テスト。

実際のSQLite（`SqliteGoldRepository`、変更なし）へ書き込んだ`GoldRecord`を、
`RepositoryExportService.export_all_with_metadata()`等（Phase6 Task14-4で
追加）経由でJSON/CSV/Parquetへ書き出し、実際に書き出したバイト列から
計算したSHA-256を含む`ExportArtifact`が返り、`GoldRecord`を一切呼び出し元
へ渡さないことを確認する。Composition Root（`cli/bootstrap.py`）は経由しない。
"""

import csv
import hashlib
import json
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from mod_personnel_db.export.service import RepositoryExportService
from mod_personnel_db.models import CandidateId, NormalizedRecord, NormalizedValue, RawRecord
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
        extracted_at=datetime(2026, 1, 1),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1),
    )


def _seed_gold_record(connection: sqlite3.Connection, person_key: str) -> None:
    candidate_id = _insert_candidate_id(connection)
    repository = SqliteGoldRepository(connection)
    repository.add_version(
        candidate_id, _make_normalized_record(), person_key, date(2026, 1, 1), "promotion"
    )


def test_export_all_with_metadata_reads_real_sqlite_and_writes_csv(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-meta-csv-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    destination = tmp_path / "export.csv"

    artifact = service.export_all_with_metadata("csv", destination)

    assert artifact.format == "csv"
    assert artifact.record_count == 1
    assert artifact.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    with open(destination, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["person_value"] == "person-meta-csv-1"


def test_export_all_with_metadata_reads_real_sqlite_and_writes_parquet(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-meta-parquet-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    destination = tmp_path / "export.parquet"

    artifact = service.export_all_with_metadata("parquet", destination)

    assert artifact.format == "parquet"
    assert artifact.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    rows = pq.read_table(destination).to_pylist()
    assert rows[0]["person_value"] == "person-meta-parquet-1"


def test_export_person_with_metadata_reads_real_sqlite_and_writes_json(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-meta-json-1")
    _seed_gold_record(connection, "person-meta-json-2")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    destination = tmp_path / "export.json"

    artifact = service.export_person_with_metadata("person-meta-json-1", "json", destination)

    assert artifact.record_count == 1
    assert artifact.sha256 == hashlib.sha256(destination.read_bytes()).hexdigest()
    payload = json.loads(destination.read_bytes().decode("utf-8"))
    assert payload[0]["person"] == {"value": "person-meta-json-1", "raw": None}


def test_export_since_with_metadata_export_id_is_unique_per_call(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-meta-since-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    since = datetime(2099, 1, 1)

    first = service.export_since_with_metadata(since, "csv", tmp_path / "first.csv")
    second = service.export_since_with_metadata(since, "csv", tmp_path / "second.csv")

    assert first.export_id != second.export_id
    assert first.sha256 == second.sha256


def test_export_all_with_metadata_exported_at_is_utc(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-meta-utc-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))

    artifact = service.export_all_with_metadata("csv", tmp_path / "export.csv")

    assert artifact.exported_at.tzinfo is not None
    assert artifact.exported_at.utcoffset() == timedelta(0)
