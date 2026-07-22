"""`PersonnelRecord`を表形式（CSV/Parquet）の1行へ平坦化する（ADR-0022、Phase6 Task14-3）。

`export/serialization.py`（JSONエクスポート用のネストした`dict`変換、本Task
では変更しない）とは別の、CSV/Parquet Writer共通の平坦な行表現を提供する。
`GoldRecord`は一切参照せず、`PersonnelRecord`のみを入力とする。
"""

from mod_personnel_db.models import NormalizedValue, PersonnelRecord

TabularValue = str | int | float | bool | None

#: CSV/Parquetの列順（両Writerで共通、スキーマの一貫性を保証する）。
TABULAR_COLUMNS: tuple[str, ...] = (
    "id",
    "person_value",
    "person_raw",
    "rank_value",
    "rank_raw",
    "organization_value",
    "organization_raw",
    "position_value",
    "position_raw",
    "appointment_type",
    "effective_date",
    "version",
    "is_current",
    "superseded_by",
    "source_pdf_content_hash",
    "source_pdf_source_url",
    "source_pdf_published_date",
    "parser_version",
    "layout_era_id",
    "confidence_score",
    "confidence_band",
)


def to_row(record: PersonnelRecord) -> dict[str, TabularValue]:
    """`PersonnelRecord`を`TABULAR_COLUMNS`に対応する平坦な1行へ変換する。"""
    provenance = record.provenance
    source_pdf = provenance.source_pdf
    return {
        "id": record.id,
        **_normalized_value_columns("person", record.person),
        **_normalized_value_columns("rank", record.rank),
        **_normalized_value_columns("organization", record.organization),
        **_normalized_value_columns("position", record.position),
        "appointment_type": record.appointment_type,
        "effective_date": record.effective_date.isoformat(),
        "version": record.version,
        "is_current": record.is_current,
        "superseded_by": record.superseded_by,
        "source_pdf_content_hash": None if source_pdf is None else source_pdf.content_hash,
        "source_pdf_source_url": None if source_pdf is None else source_pdf.source_url,
        "source_pdf_published_date": (
            None if source_pdf is None else source_pdf.published_date.isoformat()
        ),
        "parser_version": provenance.parser_version,
        "layout_era_id": provenance.layout_era_id,
        "confidence_score": record.confidence.score,
        "confidence_band": str(record.confidence.band),
    }


def _normalized_value_columns(
    prefix: str, value: NormalizedValue | None
) -> dict[str, TabularValue]:
    if value is None:
        return {f"{prefix}_value": None, f"{prefix}_raw": None}
    return {f"{prefix}_value": value.value, f"{prefix}_raw": value.raw}


__all__ = ["TABULAR_COLUMNS", "TabularValue", "to_row"]
