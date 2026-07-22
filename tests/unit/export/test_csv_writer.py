"""`export/csv_writer.py`の検証（ADR-0022、Phase6 Task14-3）。"""

import ast
import csv
import inspect
from datetime import date
from pathlib import Path

from mod_personnel_db.export import csv_writer
from mod_personnel_db.export.csv_writer import write_csv
from mod_personnel_db.export.tabular import TABULAR_COLUMNS
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
)


def test_csv_writer_module_does_not_import_gold_record() -> None:
    tree = ast.parse(inspect.getsource(csv_writer))
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


def test_write_csv_creates_header_with_tabular_columns(tmp_path: Path) -> None:
    destination = tmp_path / "out.csv"

    write_csv((), destination)

    with open(destination, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert tuple(header) == TABULAR_COLUMNS


def test_write_csv_writes_one_row_per_record(tmp_path: Path) -> None:
    destination = tmp_path / "out.csv"
    records = (_make_record("gold-1", "山田太郎"), _make_record("gold-2", "鈴木花子"))

    write_csv(records, destination)

    with open(destination, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [row["id"] for row in rows] == ["gold-1", "gold-2"]
    assert [row["person_value"] for row in rows] == ["山田太郎", "鈴木花子"]


def test_write_csv_output_is_utf8_without_bom(tmp_path: Path) -> None:
    destination = tmp_path / "out.csv"

    write_csv((_make_record("gold-1", "山田太郎"),), destination)

    raw = destination.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert "山田太郎".encode() in raw


def test_write_csv_accepts_empty_iterable(tmp_path: Path) -> None:
    destination = tmp_path / "out.csv"

    write_csv((), destination)

    with open(destination, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []
