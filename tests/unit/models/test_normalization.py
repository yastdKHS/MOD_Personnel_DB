from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    ConfidenceBand,
    KnowledgeItemId,
    NormalizationCandidate,
    NormalizationEvidence,
    NormalizationResult,
    NormalizedField,
    NormalizedRecord,
    NormalizedValue,
    RawRecord,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


def _evidence(*, matched: tuple[KnowledgeItemId, ...] = ()) -> NormalizationEvidence:
    return NormalizationEvidence(
        layout_id="format_a", knowledge_version="chk-1", matched_item_ids=matched
    )


def _raw_record() -> RawRecord:
    return RawRecord(
        section_ref=None,
        layout_id="format_a",
        record_index=0,
        raw_fields={"column_1": "山田太郎"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _normalized_record() -> NormalizedRecord:
    raw = _raw_record()
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"column_1": NormalizedValue(value="山田太郎", raw="山田太郎")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_normalized_field_normal_construction() -> None:
    field = NormalizedField(
        name="column_1", raw="山田太郎", value="山田太郎", normalization_method="alias"
    )
    assert field.value == "山田太郎"


@pytest.mark.parametrize(
    ("name", "value", "method"),
    [("", "x", "alias"), ("column_1", "", "alias"), ("column_1", "x", "")],
)
def test_normalized_field_rejects_empty_required_strings(
    name: str, value: str, method: str
) -> None:
    with pytest.raises(ModelValidationError):
        NormalizedField(name=name, raw="raw", value=value, normalization_method=method)


def test_normalization_evidence_normal_construction() -> None:
    evidence = _evidence()
    assert evidence.knowledge_version == "chk-1"


@pytest.mark.parametrize(("layout_id", "knowledge_version"), [("", "chk-1"), ("format_a", "")])
def test_normalization_evidence_rejects_empty_required_strings(
    layout_id: str, knowledge_version: str
) -> None:
    with pytest.raises(ModelValidationError):
        NormalizationEvidence(
            layout_id=layout_id, knowledge_version=knowledge_version, matched_item_ids=()
        )


def test_normalization_candidate_normal_construction() -> None:
    field = NormalizedField(
        name="column_1", raw="山田太郎", value="山田太郎", normalization_method="alias"
    )
    candidate = NormalizationCandidate(
        record_index=0, score=1.0, fields=(field,), evidence=_evidence()
    )
    assert candidate.score == 1.0


def test_normalization_candidate_rejects_negative_record_index() -> None:
    with pytest.raises(ModelValidationError):
        NormalizationCandidate(record_index=-1, score=0.5, fields=(), evidence=_evidence())


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_normalization_candidate_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        NormalizationCandidate(record_index=0, score=score, fields=(), evidence=_evidence())


def test_normalization_result_normal_construction() -> None:
    field = NormalizedField(
        name="column_1", raw="山田太郎", value="山田太郎", normalization_method="alias"
    )
    candidate = NormalizationCandidate(
        record_index=0, score=1.0, fields=(field,), evidence=_evidence()
    )
    result = NormalizationResult(
        records=(_normalized_record(),),
        candidates=(candidate,),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
    )
    assert len(result.records) == 1


def test_normalization_result_allows_empty_records() -> None:
    result = NormalizationResult(
        records=(), candidates=(), confidence=Confidence(score=0.0, band=ConfidenceBand.LOW)
    )
    assert result.records == ()
