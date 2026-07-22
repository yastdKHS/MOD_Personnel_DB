"""`export/integrity.py`の検証（ADR-0029、Phase6 Task14-4）。

SHA-256が実データ（実際に書き出すバイト列）から計算されること、
`export_id`が毎回一意であること、`exported_at`がUTCであること、
`record_count`が実件数と一致すること、JSON/CSV/Parquetそれぞれについて
同一内容なら同一SHA-256になることを検証する。
"""

import ast
import hashlib
import inspect
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from mod_personnel_db.export import integrity
from mod_personnel_db.export.csv_writer import to_csv_bytes
from mod_personnel_db.export.integrity import build_artifact, write_with_metadata
from mod_personnel_db.export.json_writer import to_json_bytes
from mod_personnel_db.export.parquet_writer import to_parquet_bytes
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    ExportFormat,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
)


def _make_record(record_id: str, person_name: str) -> PersonnelRecord:
    return PersonnelRecord(
        id=record_id,
        person=NormalizedValue(value=person_name, raw=None),
        rank=None,
        organization=None,
        position=None,
        appointment_type="promotion",
        effective_date=date(2026, 7, 1),
        version=1,
        is_current=True,
        superseded_by=None,
        provenance=Provenance(source_pdf=None, parser_version=None, layout_era_id=None),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )


def test_integrity_module_does_not_import_gold_record() -> None:
    tree = ast.parse(inspect.getsource(integrity))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "GoldRecord" not in imported_names


def test_build_artifact_sha256_matches_actual_bytes() -> None:
    data = b"hello world"

    artifact = build_artifact(data, "csv", record_count=1)

    assert artifact.sha256 == hashlib.sha256(data).hexdigest()


def test_build_artifact_exported_at_is_utc() -> None:
    artifact = build_artifact(b"data", "json", record_count=0)

    assert artifact.exported_at.tzinfo is not None
    assert artifact.exported_at.utcoffset() == timedelta(0)


def test_build_artifact_export_id_is_unique_each_call() -> None:
    first = build_artifact(b"data", "csv", record_count=0)
    second = build_artifact(b"data", "csv", record_count=0)

    assert first.export_id != second.export_id


@pytest.mark.parametrize("export_format", ["csv", "parquet", "json"])
def test_write_with_metadata_record_count_matches_actual_records(
    export_format: ExportFormat, tmp_path: Path
) -> None:
    records = (_make_record("gold-1", "山田太郎"), _make_record("gold-2", "鈴木花子"))
    destination = tmp_path / f"out.{export_format}"

    artifact = write_with_metadata(records, export_format, destination)

    assert artifact.record_count == 2
    assert artifact.format == export_format


@pytest.mark.parametrize(
    ("export_format", "to_bytes"),
    [("csv", to_csv_bytes), ("parquet", to_parquet_bytes), ("json", to_json_bytes)],
)
def test_write_with_metadata_sha256_matches_written_bytes(
    export_format: ExportFormat,
    to_bytes: Callable[[tuple[PersonnelRecord, ...]], bytes],
    tmp_path: Path,
) -> None:
    records = (_make_record("gold-1", "山田太郎"),)
    destination = tmp_path / f"out.{export_format}"

    artifact = write_with_metadata(records, export_format, destination)

    written_bytes = destination.read_bytes()
    assert artifact.sha256 == hashlib.sha256(written_bytes).hexdigest()
    assert to_bytes(records) == written_bytes


@pytest.mark.parametrize("export_format", ["csv", "parquet", "json"])
def test_write_with_metadata_same_content_yields_same_sha256_within_format(
    export_format: ExportFormat, tmp_path: Path
) -> None:
    records = (_make_record("gold-1", "山田太郎"),)

    first = write_with_metadata(records, export_format, tmp_path / "a")
    second = write_with_metadata(records, export_format, tmp_path / "b")

    assert first.sha256 == second.sha256


def test_write_with_metadata_sha256_differs_across_formats_by_design() -> None:
    """フォーマットが異なればバイト表現が異なるため、SHA-256は一致しない仕様である。"""
    records = (_make_record("gold-1", "山田太郎"),)

    csv_sha = hashlib.sha256(to_csv_bytes(records)).hexdigest()
    parquet_sha = hashlib.sha256(to_parquet_bytes(records)).hexdigest()
    json_sha = hashlib.sha256(to_json_bytes(records)).hexdigest()

    assert len({csv_sha, parquet_sha, json_sha}) == 3


def test_write_with_metadata_writes_readable_parquet(tmp_path: Path) -> None:
    records = (_make_record("gold-1", "山田太郎"),)
    destination = tmp_path / "out.parquet"

    write_with_metadata(records, "parquet", destination)

    rows = pq.read_table(destination).to_pylist()
    assert rows[0]["id"] == "gold-1"
