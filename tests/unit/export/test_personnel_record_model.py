"""`PersonnelRecord`/`SourcePdf`のValidation Rule検証（ADR-0016、Phase6 Task14-2）。

`models/export.py`はこのTaskで拡張したが、既存の慣例（`tests/unit/models/`）
に合わせたテスト配置は本Taskの対象外（`tests/unit/export/`のみ許可）の
ため、`tests/unit/export/`配下に置く。
"""

from datetime import date

import pytest

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
    SourcePdf,
)
from mod_personnel_db.models.values import ModelValidationError


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


def test_personnel_record_rejects_empty_id() -> None:
    kwargs = _base_kwargs() | {"id": ""}
    with pytest.raises(ModelValidationError, match="id must not be empty"):
        PersonnelRecord(**kwargs)  # type: ignore[arg-type]


def test_personnel_record_rejects_empty_appointment_type() -> None:
    kwargs = _base_kwargs() | {"appointment_type": ""}
    with pytest.raises(ModelValidationError, match="appointment_type must not be empty"):
        PersonnelRecord(**kwargs)  # type: ignore[arg-type]


def test_personnel_record_rejects_version_below_one() -> None:
    kwargs = _base_kwargs() | {"version": 0}
    with pytest.raises(ModelValidationError, match="version must be >= 1"):
        PersonnelRecord(**kwargs)  # type: ignore[arg-type]


def test_source_pdf_rejects_empty_content_hash() -> None:
    with pytest.raises(ModelValidationError, match="content_hash must not be empty"):
        SourcePdf(
            content_hash="",
            source_url="https://example.mod.go.jp/x.pdf",
            published_date=date(2026, 1, 1),
        )


def test_source_pdf_rejects_empty_source_url() -> None:
    with pytest.raises(ModelValidationError, match="source_url must not be empty"):
        SourcePdf(content_hash="a" * 64, source_url="", published_date=date(2026, 1, 1))
