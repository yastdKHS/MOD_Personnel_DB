from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    ConfidenceBand,
    ExtractionCandidate,
    ExtractionEvidence,
    FieldExtractionResult,
    RawField,
    RawRecord,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


def _evidence(*, column_count: int = 1) -> ExtractionEvidence:
    return ExtractionEvidence(line="山田太郎  陸将補", column_count=column_count)


def _record() -> RawRecord:
    return RawRecord(
        section_ref=None,
        record_index=0,
        raw_fields={"column_1": "山田太郎"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_raw_field_normal_construction() -> None:
    field = RawField(name="column_1", value="山田太郎")
    assert field.value == "山田太郎"


def test_raw_field_rejects_empty_name() -> None:
    with pytest.raises(ModelValidationError):
        RawField(name="", value="山田太郎")


def test_raw_field_allows_empty_value() -> None:
    field = RawField(name="column_1", value="")
    assert field.value == ""


def test_extraction_evidence_normal_construction() -> None:
    evidence = _evidence()
    assert evidence.column_count == 1


def test_extraction_evidence_rejects_negative_column_count() -> None:
    with pytest.raises(ModelValidationError):
        ExtractionEvidence(line="x", column_count=-1)


def test_extraction_candidate_normal_construction() -> None:
    field = RawField(name="column_1", value="山田太郎")
    candidate = ExtractionCandidate(
        record_index=0, score=0.8, fields=(field,), evidence=_evidence()
    )
    assert candidate.score == 0.8


def test_extraction_candidate_rejects_negative_record_index() -> None:
    with pytest.raises(ModelValidationError):
        ExtractionCandidate(record_index=-1, score=0.5, fields=(), evidence=_evidence())


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_extraction_candidate_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        ExtractionCandidate(record_index=0, score=score, fields=(), evidence=_evidence())


def test_field_extraction_result_normal_construction() -> None:
    field = RawField(name="column_1", value="山田太郎")
    candidate = ExtractionCandidate(
        record_index=0, score=1.0, fields=(field,), evidence=_evidence()
    )
    result = FieldExtractionResult(
        records=(_record(),),
        candidates=(candidate,),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )
    assert len(result.records) == 1


def test_field_extraction_result_allows_empty_records() -> None:
    result = FieldExtractionResult(
        records=(), candidates=(), confidence=Confidence(score=0.0, band=ConfidenceBand.LOW)
    )
    assert result.records == ()
