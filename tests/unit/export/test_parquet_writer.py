"""`export/parquet_writer.py`の検証（ADR-0022、Phase6 Task14-3）。"""

import ast
import inspect
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from mod_personnel_db.export import parquet_writer
from mod_personnel_db.export.parquet_writer import write_parquet
from mod_personnel_db.export.tabular import TABULAR_COLUMNS
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
)


def test_parquet_writer_module_does_not_import_gold_record() -> None:
    tree = ast.parse(inspect.getsource(parquet_writer))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "GoldRecord" not in imported_names


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


def test_write_parquet_produces_readable_table_with_tabular_columns(tmp_path: Path) -> None:
    destination = tmp_path / "out.parquet"

    write_parquet((), destination)

    table = pq.read_table(destination)
    assert tuple(table.column_names) == TABULAR_COLUMNS


def test_write_parquet_round_trips_record_values(tmp_path: Path) -> None:
    destination = tmp_path / "out.parquet"
    records = (_make_record("gold-1", "山田太郎"), _make_record("gold-2", "鈴木花子"))

    write_parquet(records, destination)

    rows = pq.read_table(destination).to_pylist()
    assert [row["id"] for row in rows] == ["gold-1", "gold-2"]
    assert [row["person_value"] for row in rows] == ["山田太郎", "鈴木花子"]
    assert rows[0]["version"] == 1
    assert rows[0]["is_current"] is True
    assert rows[0]["effective_date"] == "2026-07-01"
    assert rows[0]["confidence_score"] == 1.0


def test_write_parquet_accepts_empty_iterable(tmp_path: Path) -> None:
    destination = tmp_path / "out.parquet"

    write_parquet((), destination)

    rows = pq.read_table(destination).to_pylist()
    assert rows == []
