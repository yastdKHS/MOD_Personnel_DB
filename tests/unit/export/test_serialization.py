import json
from datetime import date

from mod_personnel_db.export.serialization import to_json_dict
from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    NormalizedValue,
    PersonnelRecord,
    Provenance,
    SourcePdf,
)


def _make_record(
    *,
    rank: NormalizedValue | None = None,
    organization: NormalizedValue | None = None,
    position: NormalizedValue | None = None,
    provenance: Provenance | None = None,
) -> PersonnelRecord:
    return PersonnelRecord(
        id="gold-00000001",
        person=NormalizedValue(value="山田太郎", raw="山田太郎"),
        rank=rank,
        organization=organization,
        position=position,
        appointment_type="promotion",
        effective_date=date(2026, 7, 1),
        version=1,
        is_current=True,
        superseded_by=None,
        provenance=provenance
        or Provenance(source_pdf=None, parser_version=None, layout_era_id="reiwa"),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )


def test_to_json_dict_is_actually_json_serializable() -> None:
    provenance = Provenance(
        source_pdf=SourcePdf(
            content_hash="a" * 64,
            source_url="https://example.mod.go.jp/x.pdf",
            published_date=date(2026, 6, 1),
        ),
        parser_version="v1.0.0",
        layout_era_id="reiwa",
    )
    record = _make_record(rank=NormalizedValue(value="大将", raw="大将?"), provenance=provenance)

    serialized = json.dumps(to_json_dict(record), ensure_ascii=False)
    reloaded = json.loads(serialized)

    assert reloaded == to_json_dict(record)


def test_to_json_dict_matches_expected_shape() -> None:
    record = _make_record(rank=NormalizedValue(value="大将", raw="大将?"))

    result = to_json_dict(record)

    assert result["id"] == "gold-00000001"
    assert result["person"] == {"value": "山田太郎", "raw": "山田太郎"}
    assert result["rank"] == {"value": "大将", "raw": "大将?"}
    assert result["organization"] is None
    assert result["position"] is None
    assert result["appointment_type"] == "promotion"
    assert result["effective_date"] == "2026-07-01"
    assert result["version"] == 1
    assert result["is_current"] is True
    assert result["superseded_by"] is None
    assert result["provenance"] == {
        "source_pdf": None,
        "parser_version": None,
        "layout_era_id": "reiwa",
    }
    assert result["confidence"] == {"score": 1.0, "band": "verified"}


def test_to_json_dict_serializes_source_pdf_when_present() -> None:
    source_pdf = SourcePdf(
        content_hash="b" * 64,
        source_url="https://example.mod.go.jp/y.pdf",
        published_date=date(2026, 5, 1),
    )
    provenance = Provenance(source_pdf=source_pdf, parser_version="v2.0.0", layout_era_id="reiwa")
    record = _make_record(provenance=provenance)

    result = to_json_dict(record)

    assert result["provenance"]["source_pdf"] == {
        "content_hash": "b" * 64,
        "source_url": "https://example.mod.go.jp/y.pdf",
        "published_date": "2026-05-01",
    }
    assert result["provenance"]["parser_version"] == "v2.0.0"


def test_to_json_dict_contains_no_non_primitive_values() -> None:
    record = _make_record(
        rank=NormalizedValue(value="大将", raw="大将?"),
        organization=NormalizedValue(value="陸上幕僚監部", raw=None),
        position=NormalizedValue(value="幕僚長", raw=None),
    )

    # dictがJSONプリミティブのみで構成されていることを、json.dumpsが
    # 例外を送出しないことで確認する（TypeErrorが出ればシリアライズ不能）。
    json.dumps(to_json_dict(record))
