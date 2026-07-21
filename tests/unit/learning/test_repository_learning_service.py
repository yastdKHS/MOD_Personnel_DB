from datetime import UTC, datetime

import pytest

from mod_personnel_db.learning import LearningService, RepositoryLearningService
from mod_personnel_db.learning.exceptions import LearningServiceError
from mod_personnel_db.models import (
    ErrorCategory,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.utils.exceptions import RepositoryError

from ._repository_stub import StubLearningRepository


def _make_entry(
    status: LearningStatus = LearningStatus.OPEN,
    error_category: ErrorCategory = ErrorCategory.KNOWLEDGE_GAP,
) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=error_category,
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


def test_record_error_delegates_to_repository() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)

    record_id = service.record_error(_make_entry())
    persisted = repo.get(record_id)

    assert persisted is not None
    assert persisted.status == LearningStatus.OPEN


def test_record_error_rejects_non_open_status() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)

    with pytest.raises(LearningServiceError):
        service.record_error(_make_entry(status=LearningStatus.IN_REVIEW))


def test_transition_open_to_in_review() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())

    updated = service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")

    assert updated.status == LearningStatus.IN_REVIEW
    assert updated.correct_value == "大将"
    assert repo.get(record_id) == updated


def test_transition_in_review_to_reflected() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())
    service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")

    updated = service.transition(
        record_id,
        LearningStatus.REFLECTED,
        git_commit_hash="abc123",
        pull_request_url="https://example.invalid/pr/1",
    )

    assert updated.status == LearningStatus.REFLECTED
    assert updated.git_commit_hash == "abc123"


def test_transition_in_review_to_wontfix() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())
    service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")

    updated = service.transition(record_id, LearningStatus.WONTFIX)

    assert updated.status == LearningStatus.WONTFIX


def test_transition_reflected_to_verified() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())
    service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")
    service.transition(record_id, LearningStatus.REFLECTED)

    updated = service.transition(
        record_id, LearningStatus.VERIFIED, regression_status=RegressionStatus.PASSED
    )

    assert updated.status == LearningStatus.VERIFIED
    assert updated.regression_status == RegressionStatus.PASSED


def test_transition_reflected_back_to_in_review_on_regression_failure() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())
    service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")
    service.transition(record_id, LearningStatus.REFLECTED)

    updated = service.transition(
        record_id, LearningStatus.IN_REVIEW, regression_status=RegressionStatus.FAILED
    )

    assert updated.status == LearningStatus.IN_REVIEW
    assert updated.regression_status == RegressionStatus.FAILED


@pytest.mark.parametrize(
    ("start_status", "illegal_target"),
    [
        (LearningStatus.OPEN, LearningStatus.REFLECTED),
        (LearningStatus.OPEN, LearningStatus.VERIFIED),
        (LearningStatus.OPEN, LearningStatus.WONTFIX),
        (LearningStatus.VERIFIED, LearningStatus.OPEN),
        (LearningStatus.WONTFIX, LearningStatus.IN_REVIEW),
    ],
)
def test_transition_illegal_edge_raises(
    start_status: LearningStatus, illegal_target: LearningStatus
) -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())
    if start_status == LearningStatus.VERIFIED:
        repo.update(
            record_id,
            status=start_status,
            correct_value="大将",
            regression_status=RegressionStatus.PASSED,
        )
    elif start_status != LearningStatus.OPEN:
        repo.update(record_id, status=start_status, correct_value="大将")

    with pytest.raises(LearningServiceError):
        service.transition(record_id, illegal_target)


def test_transition_missing_record_raises() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)

    with pytest.raises(LearningServiceError):
        service.transition(LearningRecordId(999), LearningStatus.IN_REVIEW)


def test_repository_error_propagates_unwrapped() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    record_id = service.record_error(_make_entry())

    with pytest.raises(RepositoryError):
        service.transition(
            record_id, LearningStatus.IN_REVIEW, correct_value="大将", not_a_real_field="x"
        )


def test_list_open_returns_only_open_status() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    open_id = service.record_error(_make_entry())
    reviewed_id = service.record_error(_make_entry())
    service.transition(reviewed_id, LearningStatus.IN_REVIEW, correct_value="大将")

    open_records = service.list_open()

    assert [r.id for r in open_records] == [open_id]


def test_summarize_by_error_category_counts_across_statuses() -> None:
    repo = StubLearningRepository()
    service = RepositoryLearningService(repo)
    service.record_error(_make_entry(error_category=ErrorCategory.KNOWLEDGE_GAP))
    second_id = service.record_error(_make_entry(error_category=ErrorCategory.KNOWLEDGE_GAP))
    service.transition(second_id, LearningStatus.IN_REVIEW, correct_value="大将")
    service.record_error(_make_entry(error_category=ErrorCategory.LAYOUT_GAP))

    summary = service.summarize_by_error_category()

    assert summary == {
        str(ErrorCategory.KNOWLEDGE_GAP): 2,
        str(ErrorCategory.LAYOUT_GAP): 1,
    }


def test_summarize_by_error_category_empty_repository() -> None:
    service = RepositoryLearningService(StubLearningRepository())

    assert service.summarize_by_error_category() == {}


def test_repository_learning_service_satisfies_protocol() -> None:
    service: LearningService = RepositoryLearningService(StubLearningRepository())

    record_id = service.record_error(_make_entry())

    assert service.list_open() != ()
    updated = service.transition(record_id, LearningStatus.IN_REVIEW, correct_value="大将")
    assert updated.status == LearningStatus.IN_REVIEW
    assert service.summarize_by_error_category() == {str(ErrorCategory.KNOWLEDGE_GAP): 1}


def test_repository_learning_service_public_api_matches_protocol() -> None:
    public_names = {name for name in dir(RepositoryLearningService) if not name.startswith("_")}

    assert public_names == {
        "record_error",
        "transition",
        "list_open",
        "summarize_by_error_category",
    }
