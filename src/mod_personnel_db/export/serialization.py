"""`PersonnelRecord`をJSONシリアライズ可能な`dict`へ変換する（ADR-0016、Phase6 Task14-2）。

`json.dumps()`にそのまま渡せる、`str`/`int`/`float`/`bool`/`None`/`dict`/
`list`のみで構成された構造を返す（`date`は`isoformat()`済みの文字列、
`ConfidenceBand`等の`StrEnum`は`str()`済みの文字列にする）。
"""

from typing import Any

from mod_personnel_db.models import (
    Confidence,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
    SourcePdf,
)


def to_json_dict(record: PersonnelRecord) -> dict[str, Any]:
    """`PersonnelRecord`をJSONシリアライズ可能な`dict`に変換する。"""
    return {
        "id": record.id,
        "person": _normalized_value_to_dict(record.person),
        "rank": _optional_normalized_value_to_dict(record.rank),
        "organization": _optional_normalized_value_to_dict(record.organization),
        "position": _optional_normalized_value_to_dict(record.position),
        "appointment_type": record.appointment_type,
        "effective_date": record.effective_date.isoformat(),
        "version": record.version,
        "is_current": record.is_current,
        "superseded_by": record.superseded_by,
        "provenance": _provenance_to_dict(record.provenance),
        "confidence": _confidence_to_dict(record.confidence),
    }


def _normalized_value_to_dict(value: NormalizedValue) -> dict[str, Any]:
    return {"value": value.value, "raw": value.raw}


def _optional_normalized_value_to_dict(value: NormalizedValue | None) -> dict[str, Any] | None:
    return None if value is None else _normalized_value_to_dict(value)


def _source_pdf_to_dict(source_pdf: SourcePdf) -> dict[str, Any]:
    return {
        "content_hash": source_pdf.content_hash,
        "source_url": source_pdf.source_url,
        "published_date": source_pdf.published_date.isoformat(),
    }


def _provenance_to_dict(provenance: Provenance) -> dict[str, Any]:
    source_pdf = provenance.source_pdf
    return {
        "source_pdf": None if source_pdf is None else _source_pdf_to_dict(source_pdf),
        "parser_version": provenance.parser_version,
        "layout_era_id": provenance.layout_era_id,
    }


def _confidence_to_dict(confidence: Confidence) -> dict[str, Any]:
    return {"score": confidence.score, "band": str(confidence.band)}


__all__ = ["to_json_dict"]
