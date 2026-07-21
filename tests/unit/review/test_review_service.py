from datetime import UTC, date, datetime

import pytest

from mod_personnel_db.learning import LearningService
from mod_personnel_db.learning.exceptions import LearningServiceError
from mod_personnel_db.learning.service import RepositoryLearningService
from mod_personnel_db.models import (
    CandidateId,
    ErrorCategory,
    LearningRecord,
    LearningStatus,
    NormalizedRecord,
    NormalizedValue,
    PipelineStageName,
    RawRecord,
    RegressionStatus,
)
from mod_personnel_db.repositories import GoldRepository, LearningRepository
from mod_personnel_db.review import GoldPromotion, ReviewService
from mod_personnel_db.review.service import RepositoryReviewService
from mod_personnel_db.utils.exceptions import RepositoryError

from ._stubs import StubGoldRepository, StubLearningRepository


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


def _make_normalized_record() -> NormalizedRecord:
    raw = RawRecord(
        section_ref=None,
        layout_id="reiwa",
        record_index=0,
        raw_fields={"rank": "大将?"},
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return NormalizedRecord(
        raw_record_ref=raw,
        normalized_fields={"rank": NormalizedValue(value="大将", raw="大将?")},
        normalization_applied=(),
        normalized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_service() -> tuple[RepositoryReviewService, StubLearningRepository, StubGoldRepository]:
    learning_repository = StubLearningRepository()
    gold_repository = StubGoldRepository()
    learning_service = RepositoryLearningService(learning_repository)
    service = RepositoryReviewService(learning_repository, gold_repository, learning_service)
    return service, learning_repository, gold_repository


def test_list_pending_returns_only_open_status() -> None:
    service, learning_repository, _ = _make_service()
    open_id = learning_repository.add(_make_entry())
    reviewed_id = learning_repository.add(_make_entry())
    learning_repository.update(reviewed_id, status=LearningStatus.IN_REVIEW, correct_value="大将")

    pending = service.list_pending()

    assert [r.id for r in pending] == [open_id]


def test_start_review_transitions_open_to_in_review() -> None:
    service, learning_repository, _ = _make_service()
    record_id = learning_repository.add(_make_entry())

    updated = service.start_review(record_id, correct_value="大将")

    assert updated.status == LearningStatus.IN_REVIEW
    assert updated.correct_value == "大将"


def test_approve_transitions_in_review_to_reflected() -> None:
    service, learning_repository, _ = _make_service()
    record_id = learning_repository.add(_make_entry())
    service.start_review(record_id, correct_value="大将")

    updated = service.approve(record_id)

    assert updated.status == LearningStatus.REFLECTED


def test_reject_transitions_in_review_to_wontfix() -> None:
    service, learning_repository, _ = _make_service()
    record_id = learning_repository.add(_make_entry())
    service.start_review(record_id, correct_value="大将")

    updated = service.reject(record_id)

    assert updated.status == LearningStatus.WONTFIX


def test_approve_with_gold_promotion_delegates_to_gold_repository() -> None:
    service, learning_repository, gold_repository = _make_service()
    record_id = learning_repository.add(_make_entry())
    service.start_review(record_id, correct_value="大将")
    normalized = _make_normalized_record()
    promotion = GoldPromotion(
        candidate_id=CandidateId(1),
        record=normalized,
        person_key="person-1",
        effective_date=date(2026, 1, 1),
        appointment_type="promotion",
    )

    service.approve(record_id, gold_promotion=promotion)

    assert gold_repository.add_version_calls == [
        (promotion.candidate_id, normalized, "person-1", date(2026, 1, 1), "promotion")
    ]
    stored = gold_repository.get_current("person-1", date(2026, 1, 1))
    assert stored is not None
    assert stored.fields == normalized


def test_approve_without_gold_promotion_does_not_call_gold_repository() -> None:
    service, learning_repository, gold_repository = _make_service()
    record_id = learning_repository.add(_make_entry())
    service.start_review(record_id, correct_value="大将")

    service.approve(record_id)

    assert gold_repository.add_version_calls == []


def test_learning_service_transition_illegality_propagates() -> None:
    service, learning_repository, _ = _make_service()
    record_id = learning_repository.add(_make_entry())

    with pytest.raises(LearningServiceError):
        service.approve(record_id)


def test_repository_error_propagates_unwrapped() -> None:
    service, learning_repository, _ = _make_service()
    record_id = learning_repository.add(_make_entry())

    with pytest.raises(RepositoryError):
        service.start_review(record_id, correct_value="大将", not_a_real_field="x")


def test_review_service_satisfies_protocol() -> None:
    learning_repository = StubLearningRepository()
    gold_repository = StubGoldRepository()
    learning_service: LearningService = RepositoryLearningService(learning_repository)
    typed_learning_repository: LearningRepository = learning_repository
    typed_gold_repository: GoldRepository = gold_repository

    service: ReviewService = RepositoryReviewService(
        typed_learning_repository, typed_gold_repository, learning_service
    )

    record_id = learning_repository.add(_make_entry())
    assert service.list_pending() != ()
    updated = service.start_review(record_id, correct_value="大将")
    assert updated.status == LearningStatus.IN_REVIEW


def test_review_service_public_api_matches_protocol() -> None:
    public_names = {name for name in dir(RepositoryReviewService) if not name.startswith("_")}

    assert public_names == {"list_pending", "start_review", "approve", "reject"}
