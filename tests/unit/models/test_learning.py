from datetime import UTC, datetime

import pytest

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    ErrorCategory,
    LearningRecord,
    LearningStatus,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.models.values import ModelValidationError

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _make_record(
    status: LearningStatus = LearningStatus.OPEN,
    correct_value: str | None = None,
    regression_status: RegressionStatus = RegressionStatus.NOT_RUN,
) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.NORMALIZER,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="陸将補（誤）",
        correct_value=correct_value,
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=Confidence(score=0.3, band=ConfidenceBand.LOW),
        status=status,
        reflected_in_knowledge_item_id=None,
        reflected_in_layout_id=None,
        git_commit_hash=None,
        pull_request_url=None,
        regression_status=regression_status,
        regression_run_at=None,
        regression_details=None,
        improvement_candidate=None,
        created_at=_CREATED_AT,
        resolved_at=None,
    )


def test_learning_record_normal_open_state() -> None:
    record = _make_record()

    assert record.status is LearningStatus.OPEN
    assert record.correct_value is None
    assert record.pipeline_stage is PipelineStageName.NORMALIZER


def test_learning_record_in_review_requires_correct_value() -> None:
    with pytest.raises(ModelValidationError):
        _make_record(status=LearningStatus.IN_REVIEW, correct_value=None)


def test_learning_record_in_review_with_correct_value_is_valid() -> None:
    record = _make_record(status=LearningStatus.IN_REVIEW, correct_value="陸将補")
    assert record.correct_value == "陸将補"


def test_learning_record_wontfix_also_requires_correct_value() -> None:
    # status != "open" は wontfix を含め correct_value を要求する（models.md記載どおり）。
    with pytest.raises(ModelValidationError):
        _make_record(status=LearningStatus.WONTFIX, correct_value=None)


def test_learning_record_verified_requires_regression_passed() -> None:
    with pytest.raises(ModelValidationError):
        _make_record(
            status=LearningStatus.VERIFIED,
            correct_value="陸将補",
            regression_status=RegressionStatus.NOT_RUN,
        )


def test_learning_record_verified_with_regression_passed_is_valid() -> None:
    record = _make_record(
        status=LearningStatus.VERIFIED,
        correct_value="陸将補",
        regression_status=RegressionStatus.PASSED,
    )
    assert record.status is LearningStatus.VERIFIED


@pytest.mark.parametrize(
    "stage",
    [
        PipelineStageName.LAYOUT_DETECTOR,
        PipelineStageName.SECTION_PARSER,
        PipelineStageName.FIELD_EXTRACTOR,
        PipelineStageName.NORMALIZER,
        PipelineStageName.VALIDATOR,
    ],
)
def test_pipeline_stage_enum_members(stage: PipelineStageName) -> None:
    assert isinstance(stage.value, str)


@pytest.mark.parametrize(
    "category",
    [
        ErrorCategory.UNKNOWN_ALIAS,
        ErrorCategory.UNKNOWN_LAYOUT,
        ErrorCategory.KNOWLEDGE_GAP,
        ErrorCategory.LAYOUT_GAP,
        ErrorCategory.TRUE_EXCEPTION,
    ],
)
def test_error_category_enum_members(category: ErrorCategory) -> None:
    assert isinstance(category.value, str)
