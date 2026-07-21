import dataclasses
from datetime import UTC, date, datetime

from mod_personnel_db.export.mapper import to_personnel_record
from mod_personnel_db.models import (
    CandidateId,
    ConfidenceBand,
    GoldRecord,
    GoldRecordId,
    NormalizedRecord,
    NormalizedValue,
    RawRecord,
)


def _make_normalized_record(
    raw_fields: dict[str, str],
    normalized_fields: dict[str, NormalizedValue],
    layout_id: str = "reiwa",
) -> NormalizedRecord:
    raw = RawRecord(
        section_ref=None,
        layout_id=layout_id,
        record_index=0,
        raw_fields=raw_fields,
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields=normalized_fields,
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_gold_record(
    *,
    record_id: int = 1,
    person_key: str = "person-1",
    normalized_fields: dict[str, NormalizedValue] | None = None,
    layout_id: str = "reiwa",
) -> GoldRecord:
    fields = normalized_fields or {"column_1": NormalizedValue(value="大将", raw="大将?")}
    raw = {name: v.raw or v.value for name, v in fields.items()}
    return GoldRecord(
        id=GoldRecordId(record_id),
        candidate_id=CandidateId(1),
        person_key=person_key,
        effective_date=date(2026, 1, 1),
        appointment_type="promotion",
        fields=_make_normalized_record(raw, fields, layout_id=layout_id),
        version=1,
        is_current=True,
        superseded_by=None,
    )


def test_to_personnel_record_maps_identity_fields() -> None:
    gold = _make_gold_record(record_id=12345, person_key="yamada-taro")

    record = to_personnel_record(gold)

    assert record.id == "gold-00012345"
    assert record.person == NormalizedValue(value="yamada-taro", raw=None)
    assert record.appointment_type == "promotion"
    assert record.effective_date == date(2026, 1, 1)
    assert record.version == 1
    assert record.is_current is True
    assert record.superseded_by is None


def test_to_personnel_record_formats_superseded_by_as_public_id() -> None:
    gold = dataclasses.replace(_make_gold_record(record_id=1), superseded_by=GoldRecordId(99))

    record = to_personnel_record(gold)

    assert record.superseded_by == "gold-00000099"


def test_to_personnel_record_resolves_semantic_fields_when_keys_match() -> None:
    fields = {
        "rank": NormalizedValue(value="大将", raw="大将?"),
        "organization": NormalizedValue(value="陸上幕僚監部", raw="陸上幕僚監部"),
        "position": NormalizedValue(value="幕僚長", raw="幕僚長"),
    }
    gold = _make_gold_record(normalized_fields=fields)

    record = to_personnel_record(gold)

    assert record.rank == fields["rank"]
    assert record.organization == fields["organization"]
    assert record.position == fields["position"]


def test_to_personnel_record_leaves_semantic_fields_none_for_column_keyed_data() -> None:
    fields = {
        "column_1": NormalizedValue(value="高橋一郎", raw="髙橋一郎"),
        "column_2": NormalizedValue(value="三等陸佐", raw="三等陸佐"),
    }
    gold = _make_gold_record(normalized_fields=fields)

    record = to_personnel_record(gold)

    assert record.rank is None
    assert record.organization is None
    assert record.position is None


def test_to_personnel_record_derives_layout_era_id_from_raw_record() -> None:
    gold = _make_gold_record(layout_id="2026_format_sample")

    record = to_personnel_record(gold)

    assert record.provenance.layout_era_id == "2026_format_sample"


def test_to_personnel_record_leaves_source_pdf_and_parser_version_none() -> None:
    gold = _make_gold_record()

    record = to_personnel_record(gold)

    assert record.provenance.source_pdf is None
    assert record.provenance.parser_version is None


def test_to_personnel_record_confidence_is_always_verified() -> None:
    gold = _make_gold_record()

    record = to_personnel_record(gold)

    assert record.confidence.score == 1.0
    assert record.confidence.band == ConfidenceBand.VERIFIED


def test_to_personnel_record_does_not_expose_gold_record() -> None:
    gold = _make_gold_record()

    record = to_personnel_record(gold)

    for field in dataclasses.fields(record):
        assert not isinstance(getattr(record, field.name), GoldRecord)
