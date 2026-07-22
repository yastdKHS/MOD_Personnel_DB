"""`export/json_writer.py`の検証（ADR-0022/ADR-0029、Phase6 Task14-4）。"""

import ast
import inspect
import json
from datetime import date
from pathlib import Path

from mod_personnel_db.export import json_writer
from mod_personnel_db.export.json_writer import to_json_bytes, write_json
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
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


def test_json_writer_module_does_not_import_gold_record() -> None:
    tree = ast.parse(inspect.getsource(json_writer))
    imported_names = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "GoldRecord" not in imported_names


def test_to_json_bytes_produces_utf8_json_array() -> None:
    records = (_make_record("gold-1", "山田太郎"), _make_record("gold-2", "鈴木花子"))

    data = to_json_bytes(records)
    payload = json.loads(data.decode("utf-8"))

    assert [row["id"] for row in payload] == ["gold-1", "gold-2"]
    assert payload[0]["person"] == {"value": "山田太郎", "raw": None}
    assert "山田太郎".encode() in data


def test_to_json_bytes_accepts_empty_iterable() -> None:
    assert json.loads(to_json_bytes(()).decode("utf-8")) == []


def test_write_json_writes_file(tmp_path: Path) -> None:
    destination = tmp_path / "out.json"

    write_json((_make_record("gold-1", "山田太郎"),), destination)

    payload = json.loads(destination.read_bytes().decode("utf-8"))
    assert len(payload) == 1
    assert payload[0]["id"] == "gold-1"
