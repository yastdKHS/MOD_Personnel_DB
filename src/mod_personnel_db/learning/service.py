"""LearningServiceのRepository委譲による具象実装。docs/api/interfaces.md#learningservice
に対応する。

責務はLearning Datasetのライフサイクル管理（新規記録時の初期状態強制、
状態遷移グラフ（docs/architecture/learning_dataset.md#ライフサイクル）の
合法性判定、未反映エントリ・カテゴリ別集計の提供）のみに限定する
（ADR-0044〜ADR-0046）。永続化はコンストラクタ注入された`LearningRepository`
へ完全委譲し、SQL・SQLite・Repositoryの内部構造は一切知らない。
"""

from mod_personnel_db.learning.exceptions import LearningServiceError
from mod_personnel_db.models import ErrorCategory, LearningRecord, LearningRecordId, LearningStatus
from mod_personnel_db.repositories import LearningRepository

# docs/architecture/learning_dataset.md#ライフサイクル のMermaid状態遷移図に対応する。
_LEGAL_TRANSITIONS: dict[LearningStatus, frozenset[LearningStatus]] = {
    LearningStatus.OPEN: frozenset({LearningStatus.IN_REVIEW}),
    LearningStatus.IN_REVIEW: frozenset({LearningStatus.REFLECTED, LearningStatus.WONTFIX}),
    LearningStatus.REFLECTED: frozenset({LearningStatus.VERIFIED, LearningStatus.IN_REVIEW}),
    LearningStatus.VERIFIED: frozenset(),
    LearningStatus.WONTFIX: frozenset(),
}


class RepositoryLearningService:
    """`LearningRepository`へ永続化を委譲する`LearningService`実装。"""

    def __init__(self, repository: LearningRepository) -> None:
        self._repository = repository

    def record_error(self, entry: LearningRecord) -> LearningRecordId:
        if entry.status != LearningStatus.OPEN:
            raise LearningServiceError(
                f"new LearningRecord must start in status='open', got {entry.status!r}"
            )
        return self._repository.add(entry)

    def transition(
        self, record_id: LearningRecordId, new_status: LearningStatus, **fields: object
    ) -> LearningRecord:
        current = self._repository.get(record_id)
        if current is None:
            raise LearningServiceError(f"learning record not found: {record_id!r}")
        if new_status not in _LEGAL_TRANSITIONS.get(current.status, frozenset()):
            raise LearningServiceError(
                f"illegal status transition: {current.status!r} -> {new_status!r}"
            )
        return self._repository.update(record_id, status=new_status, **fields)

    def list_open(self) -> tuple[LearningRecord, ...]:
        return self._repository.list_by_status(LearningStatus.OPEN)

    def summarize_by_error_category(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for category in ErrorCategory:
            count = len(self._repository.list_by_error_category(str(category)))
            if count > 0:
                summary[str(category)] = count
        return summary


__all__ = ["RepositoryLearningService"]
