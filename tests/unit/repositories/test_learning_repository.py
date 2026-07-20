"""LearningRepository Protocol契約の構造適合テスト（Phase3 Task10-0.2）。

SQLite等の具象実装は本タスクの対象外のため、テスト専用のStubで
Protocol適合をmypy・実行時の両方で確認する。
"""

import dataclasses
from datetime import UTC, datetime

from mod_personnel_db.models import (
    ErrorCategory,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    ParserVersionId,
    PipelineStageName,
    RegressionStatus,
)
from mod_personnel_db.repositories import LearningRepository


class _StubLearningRepository:
    """LearningRepository Protocolを満たす、メモリ上のdictで代用する最小限のStub。"""

    def __init__(self) -> None:
        self._records: dict[int, LearningRecord] = {}
        self._next_id = 1

    def add(self, record: LearningRecord) -> LearningRecordId:
        record_id = LearningRecordId(self._next_id)
        self._next_id += 1
        self._records[int(record_id)] = record
        return record_id

    def update(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        current = self._records[int(record_id)]
        updated = dataclasses.replace(current, **fields)  # type: ignore[arg-type]
        self._records[int(record_id)] = updated
        return updated

    def get(self, record_id: LearningRecordId) -> LearningRecord | None:
        return self._records.get(int(record_id))

    def list_by_status(self, status: LearningStatus) -> tuple[LearningRecord, ...]:
        return tuple(r for r in self._records.values() if r.status == status)

    def list_by_error_category(self, category: str) -> tuple[LearningRecord, ...]:
        return tuple(r for r in self._records.values() if str(r.error_category) == category)

    def list_by_parser_version(
        self, parser_version_id: ParserVersionId
    ) -> tuple[LearningRecord, ...]:
        return tuple(r for r in self._records.values() if r.parser_version_id == parser_version_id)


def _make_record() -> LearningRecord:
    return LearningRecord(
        id=None,
        source_candidate_id=None,
        source_review_item_id=None,
        pipeline_stage=PipelineStageName.VALIDATOR,
        error_category=ErrorCategory.KNOWLEDGE_GAP,
        field_name="rank",
        wrong_value="大将?",
        correct_value=None,
        correction_summary=None,
        reviewer_comment=None,
        parser_version_id=None,
        layout_id=None,
        confidence=None,
        status=LearningStatus.OPEN,
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


def test_stub_satisfies_learning_repository_protocol() -> None:
    repo: LearningRepository = _StubLearningRepository()

    record_id = repo.add(_make_record())

    assert repo.get(record_id) is not None
    assert len(repo.list_by_status(LearningStatus.OPEN)) == 1
    assert len(repo.list_by_error_category(str(ErrorCategory.KNOWLEDGE_GAP))) == 1
    assert repo.list_by_parser_version(ParserVersionId(1)) == ()

    updated = repo.update(record_id, status=LearningStatus.IN_REVIEW, correct_value="大将")
    assert updated.status == LearningStatus.IN_REVIEW


def test_learning_repository_public_api_is_documented_methods() -> None:
    public_names = {name for name in dir(LearningRepository) if not name.startswith("_")}

    assert public_names == {
        "add",
        "update",
        "get",
        "list_by_status",
        "list_by_error_category",
        "list_by_parser_version",
    }
