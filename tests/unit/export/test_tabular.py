"""`export/tabular.py`の平坦化ロジックの検証（ADR-0022、Phase6 Task14-3）。"""

from datetime import date

from mod_personnel_db.export.tabular import TABULAR_COLUMNS, to_row
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
    SourcePdf,
)


def _base_kwargs() -> dict[str, object]:
    return {
        "id": "gold-00000001",
        "person": NormalizedValue(value="山田太郎", raw=None),
        "rank": None,
        "organization": None,
        "position": None,
        "appointment_type": "promotion",
        "effective_date": date(2026, 7, 1),
        "version": 1,
        "is_current": True,
        "superseded_by": None,
        "provenance": Provenance(source_pdf=None, parser_version=None, layout_era_id=None),
        "confidence": Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    }


def test_to_row_keys_match_tabular_columns() -> None:
    record = PersonnelRecord(**_base_kwargs())  # type: ignore[arg-type]

    row = to_row(record)

    assert tuple(row.keys()) == TABULAR_COLUMNS


def test_to_row_flattens_normalized_values() -> None:
    kwargs = _base_kwargs() | {
        "rank": NormalizedValue(value="大将", raw="大将?"),
    }
    record = PersonnelRecord(**kwargs)  # type: ignore[arg-type]

    row = to_row(record)

    assert row["person_value"] == "山田太郎"
    assert row["person_raw"] is None
    assert row["rank_value"] == "大将"
    assert row["rank_raw"] == "大将?"
    assert row["organization_value"] is None
    assert row["organization_raw"] is None


def test_to_row_handles_none_source_pdf() -> None:
    record = PersonnelRecord(**_base_kwargs())  # type: ignore[arg-type]

    row = to_row(record)

    assert row["source_pdf_content_hash"] is None
    assert row["source_pdf_source_url"] is None
    assert row["source_pdf_published_date"] is None


def test_to_row_flattens_source_pdf_when_present() -> None:
    kwargs = _base_kwargs() | {
        "provenance": Provenance(
            source_pdf=SourcePdf(
                content_hash="a" * 64,
                source_url="https://example.mod.go.jp/x.pdf",
                published_date=date(2026, 1, 1),
            ),
            parser_version="1.0.0",
            layout_era_id="reiwa",
        ),
    }
    record = PersonnelRecord(**kwargs)  # type: ignore[arg-type]

    row = to_row(record)

    assert row["source_pdf_content_hash"] == "a" * 64
    assert row["source_pdf_source_url"] == "https://example.mod.go.jp/x.pdf"
    assert row["source_pdf_published_date"] == "2026-01-01"
    assert row["parser_version"] == "1.0.0"
    assert row["layout_era_id"] == "reiwa"


def test_to_row_serializes_scalar_fields() -> None:
    record = PersonnelRecord(**_base_kwargs())  # type: ignore[arg-type]

    row = to_row(record)

    assert row["id"] == "gold-00000001"
    assert row["appointment_type"] == "promotion"
    assert row["effective_date"] == "2026-07-01"
    assert row["version"] == 1
    assert row["is_current"] is True
    assert row["superseded_by"] is None
    assert row["confidence_score"] == 1.0
    assert row["confidence_band"] == str(ConfidenceBand.VERIFIED)
