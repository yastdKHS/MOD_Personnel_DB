"""ExportServiceのCSV/Parquet公開API（ADR-0022）の結合テスト。

実際のSQLite（`SqliteGoldRepository`、変更なし）へ書き込んだ`GoldRecord`を、
`RepositoryExportService.export_all_csv()`/`export_all_parquet()`（Phase6
Task14-3で追加）経由でファイルへ書き出し、実際にCSV（UTF-8、BOMなし）・
Parquetとして読み戻せることを確認する。Composition Root（`cli/bootstrap.py`）
は経由しない。
"""

import csv
import sqlite3
import uuid
from datetime import date, datetime
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


def test_export_all_csv_reads_real_sqlite_and_writes_readable_csv(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-csv-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    destination = tmp_path / "export.csv"

    service.export_all_csv(destination)

    raw = destination.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    with open(destination, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["person_value"] == "person-csv-1"
    assert rows[0]["layout_era_id"] == "2026_format_sample"


def test_export_all_parquet_reads_real_sqlite_and_writes_readable_parquet(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-parquet-1")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    destination = tmp_path / "export.parquet"

    service.export_all_parquet(destination)

    rows = pq.read_table(destination).to_pylist()
    assert len(rows) == 1
    assert rows[0]["person_value"] == "person-parquet-1"
    assert rows[0]["layout_era_id"] == "2026_format_sample"


def test_export_all_csv_and_parquet_contain_same_records(
    connection: sqlite3.Connection, tmp_path: Path
) -> None:
    _seed_gold_record(connection, "person-both-1")
    _seed_gold_record(connection, "person-both-2")
    service = RepositoryExportService(SqliteGoldRepository(connection))
    csv_destination = tmp_path / "export.csv"
    parquet_destination = tmp_path / "export.parquet"

    service.export_all_csv(csv_destination)
    service.export_all_parquet(parquet_destination)

    with open(csv_destination, encoding="utf-8", newline="") as f:
        csv_ids = {row["id"] for row in csv.DictReader(f)}
    parquet_ids = {row["id"] for row in pq.read_table(parquet_destination).to_pylist()}
    assert csv_ids == parquet_ids
    assert len(csv_ids) == 2
