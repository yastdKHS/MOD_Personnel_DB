import sqlite3
from datetime import datetime

import pytest

from mod_personnel_db.models import (
    Confidence,
    ConfidenceBand,
    ErrorCategory,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    ParserVersionId,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.repositories import LearningRepository
from mod_personnel_db.repositories.sqlite.learning import SqliteLearningRepository
from mod_personnel_db.utils.exceptions import RepositoryError


def _make_record(
    status: LearningStatus = LearningStatus.OPEN,
    correct_value: str | None = None,
    regression_status: RegressionStatus = RegressionStatus.NOT_RUN,
    confidence: Confidence | None = None,
    parser_version_id: ParserVersionId | None = None,
) -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.NORMALIZER,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        correct_value=correct_value,
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=parser_version_id,
        layout_id=None,
        confidence=confidence,
        status=status,
        reflected_in_knowledge_item_id=None,
        reflected_in_layout_id=None,
        git_commit_hash=None,
        pull_request_url=None,
        regression_status=regression_status,
        regression_run_at=None,
        regression_details=None,
        improvement_candidate=None,
        created_at=datetime(2026, 1, 1),
        resolved_at=None,
    )


def test_add_and_get(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    fetched = repo.get(record_id)

    assert fetched is not None
    assert fetched.id == record_id
    assert fetched.pipeline_stage == PipelineStageName.NORMALIZER
    assert fetched.error_category == ErrorCategory.KNOWLEDGE_GAP
    assert fetched.wrong_value == "大将?"
    assert fetched.status == LearningStatus.OPEN
    assert fetched.regression_status == RegressionStatus.NOT_RUN
    assert fetched.confidence is None
    assert fetched.created_at == datetime(2026, 1, 1)


def test_get_missing_returns_none(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    assert repo.get(LearningRecordId(999)) is None


def test_confidence_round_trips(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    confidence = Confidence(score=0.42, band=ConfidenceBand.LOW)
    record_id = repo.add(_make_record(confidence=confidence))

    fetched = repo.get(record_id)

    assert fetched is not None
    assert fetched.confidence == confidence


def test_update_sets_lifecycle_fields(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    updated = repo.update(
        record_id,
        status=LearningStatus.IN_REVIEW,
        correct_value="大将",
        reviewer_comment="要確認",
    )

    assert updated.status == LearningStatus.IN_REVIEW
    assert updated.correct_value == "大将"
    assert updated.reviewer_comment == "要確認"
    refetched = repo.get(record_id)
    assert refetched == updated


def test_update_confidence_field(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())
    confidence = Confidence(score=0.9, band=ConfidenceBand.HIGH)

    updated = repo.update(record_id, confidence=confidence)
    assert updated.confidence == confidence

    cleared = repo.update(record_id, confidence=None)
    assert cleared.confidence is None


def test_update_datetime_field(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())
    resolved_at = datetime(2026, 3, 1)

    updated = repo.update(record_id, resolved_at=resolved_at)

    assert updated.resolved_at == resolved_at


def test_update_field_to_none(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())
    repo.update(record_id, reviewer_comment="要確認")

    reverted = repo.update(record_id, reviewer_comment=None)

    assert reverted.reviewer_comment is None


def test_update_invalid_datetime_type_raises(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    with pytest.raises(RepositoryError):
        repo.update(record_id, resolved_at="2026-03-01")


def test_update_invalid_confidence_type_raises(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    with pytest.raises(RepositoryError):
        repo.update(record_id, confidence="high")


def test_update_unknown_field_raises(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    with pytest.raises(RepositoryError):
        repo.update(record_id, not_a_real_field="x")


def test_update_missing_record_raises(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)

    with pytest.raises(RepositoryError):
        repo.update(LearningRecordId(999), status=LearningStatus.IN_REVIEW)


def test_update_missing_record_without_fields_raises(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)

    with pytest.raises(RepositoryError):
        repo.update(LearningRecordId(999))


def test_update_without_fields_returns_current_record(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    unchanged = repo.update(record_id)

    assert unchanged == repo.get(record_id)


def test_list_by_status(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    open_id = repo.add(_make_record())
    reviewed_id = repo.add(_make_record())
    repo.update(reviewed_id, status=LearningStatus.IN_REVIEW, correct_value="大将")

    open_records = repo.list_by_status(LearningStatus.OPEN)
    reviewed_records = repo.list_by_status(LearningStatus.IN_REVIEW)

    assert [r.id for r in open_records] == [open_id]
    assert [r.id for r in reviewed_records] == [reviewed_id]


def test_list_by_error_category(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    matched = repo.list_by_error_category("knowledge_gap")
    unmatched = repo.list_by_error_category("layout_gap")

    assert [r.id for r in matched] == [record_id]
    assert unmatched == ()


def test_list_by_parser_version(
    conn: sqlite3.Connection, parser_version_id: ParserVersionId
) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record(parser_version_id=parser_version_id))
    repo.add(_make_record(parser_version_id=None))

    matched = repo.list_by_parser_version(parser_version_id)

    assert [r.id for r in matched] == [record_id]


def test_verified_status_round_trip(conn: sqlite3.Connection) -> None:
    repo = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    updated = repo.update(
        record_id,
        status=LearningStatus.VERIFIED,
        correct_value="大将",
        regression_status=RegressionStatus.PASSED,
        regression_run_at=datetime(2026, 2, 1),
    )

    assert updated.status == LearningStatus.VERIFIED
    assert updated.regression_status == RegressionStatus.PASSED
    assert updated.regression_run_at == datetime(2026, 2, 1)


def test_sqlite_learning_repository_satisfies_protocol(conn: sqlite3.Connection) -> None:
    repo: LearningRepository = SqliteLearningRepository(conn)
    record_id = repo.add(_make_record())

    assert repo.get(record_id) is not None
    assert repo.list_by_status(LearningStatus.OPEN) != ()
    assert repo.list_by_error_category("knowledge_gap") != ()
    assert repo.list_by_parser_version(ParserVersionId(999)) == ()
