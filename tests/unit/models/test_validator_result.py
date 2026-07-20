from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    ConfidenceBand,
    ValidationCandidate,
    ValidationError,
    ValidationEvidence,
    ValidationResult,
    ValidationWarning,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


def _evidence(*, rules_evaluated: int = 1) -> ValidationEvidence:
    return ValidationEvidence(record_index=0, layout_id="format_a", rules_evaluated=rules_evaluated)


def test_validation_error_normal_construction() -> None:
    error = ValidationError(rule_id="validation.rank.allowed_value_set", message="不明の階級")
    assert error.rule_id == "validation.rank.allowed_value_set"


@pytest.mark.parametrize(("rule_id", "message"), [("", "x"), ("r", "")])
def test_validation_error_rejects_empty_required_strings(rule_id: str, message: str) -> None:
    with pytest.raises(ModelValidationError):
        ValidationError(rule_id=rule_id, message=message)


def test_validation_warning_normal_construction() -> None:
    warning = ValidationWarning(rule_id="layout.unmapped_field", message="no mapping")
    assert warning.rule_id == "layout.unmapped_field"


@pytest.mark.parametrize(("rule_id", "message"), [("", "x"), ("r", "")])
def test_validation_warning_rejects_empty_required_strings(rule_id: str, message: str) -> None:
    with pytest.raises(ModelValidationError):
        ValidationWarning(rule_id=rule_id, message=message)


def test_validation_evidence_normal_construction() -> None:
    evidence = _evidence()
    assert evidence.rules_evaluated == 1


@pytest.mark.parametrize(
    ("record_index", "layout_id", "rules_evaluated"),
    [(-1, "format_a", 0), (0, "", 0), (0, "format_a", -1)],
)
def test_validation_evidence_rejects_invalid_values(
    record_index: int, layout_id: str, rules_evaluated: int
) -> None:
    with pytest.raises(ModelValidationError):
        ValidationEvidence(
            record_index=record_index, layout_id=layout_id, rules_evaluated=rules_evaluated
        )


def test_validation_candidate_normal_construction() -> None:
    candidate = ValidationCandidate(
        record_index=0, score=1.0, errors=(), warnings=(), evidence=_evidence()
    )
    assert candidate.score == 1.0


def test_validation_candidate_rejects_negative_record_index() -> None:
    with pytest.raises(ModelValidationError):
        ValidationCandidate(
            record_index=-1, score=0.5, errors=(), warnings=(), evidence=_evidence()
        )


@pytest.mark.parametrize("score", [-0.1, 1.1])
def test_validation_candidate_rejects_out_of_range_score(score: float) -> None:
    with pytest.raises(ModelValidationError):
        ValidationCandidate(
            record_index=0, score=score, errors=(), warnings=(), evidence=_evidence()
        )


def test_validation_result_normal_construction() -> None:
    candidate = ValidationCandidate(
        record_index=0, score=1.0, errors=(), warnings=(), evidence=_evidence()
    )
    result = ValidationResult(
        status="passed",
        candidates=(candidate,),
        confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
        validated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.status == "passed"


def test_validation_result_rejects_failed_status_without_error() -> None:
    candidate = ValidationCandidate(
        record_index=0, score=1.0, errors=(), warnings=(), evidence=_evidence()
    )
    with pytest.raises(ModelValidationError):
        ValidationResult(
            status="failed",
            candidates=(candidate,),
            confidence=Confidence(score=1.0, band=ConfidenceBand.VERIFIED),
            validated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_validation_result_rejects_passed_status_with_error() -> None:
    candidate = ValidationCandidate(
        record_index=0,
        score=0.0,
        errors=(ValidationError(rule_id="r", message="m"),),
        warnings=(),
        evidence=_evidence(),
    )
    with pytest.raises(ModelValidationError):
        ValidationResult(
            status="passed",
            candidates=(candidate,),
            confidence=Confidence(score=0.0, band=ConfidenceBand.LOW),
            validated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
