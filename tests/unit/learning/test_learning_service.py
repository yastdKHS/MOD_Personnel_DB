from datetime import UTC, datetime

from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import (
    ErrorCategory,
    LearningRecord,
    LearningStatus,
    PipelineStageName,
    RegressionStatus,
)

from ._stubs import StubLearningService


def _make_entry(status: LearningStatus = LearningStatus.OPEN) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        correct_value="大将" if status != LearningStatus.OPEN else None,
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=None,
        status=status,
        reflected_in_knowledge_item_id=None,
        reflected_in_layout_id=None,
        git_commit_hash=None,
        pull_request_url=None,
        regression_status=RegressionStatus.NOT_RUN,
        regression_run_at=None,
        regression_details=None,
        improvement_candidate=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        resolved_at=None,
    )


def test_stub_satisfies_learning_service_protocol() -> None:
    service: LearningService = StubLearningService()

    record_id = service.record_error(_make_entry())

    assert [r.status for r in service.list_open()] == [LearningStatus.OPEN]

    updated = service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")
    assert updated.status == LearningStatus.IN_REVIEW
    assert service.list_open() == ()

    summary = service.summarize_by_error_category()
    assert summary == {str(ErrorCategory.KNOWLEDGE_GAP): 1}


def test_learning_service_public_api_is_documented_methods() -> None:
    public_names = {name for name in dir(LearningService) if not name.startswith("_")}

    assert public_names == {
        "record_error",
        "transition",
        "list_open",
        "summarize_by_error_category",
    }
