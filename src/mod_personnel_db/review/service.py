"""ReviewServiceのRepository/LearningService委譲による具象実装。
docs/adr/0021-review-ui-strategy.mdに対応する。

責務はLearning Datasetエントリのレビュー結果反映のみに限定する。

- `list_pending`: `LearningRepository`からレビュー待ち（`status='open'`）
  エントリを取得する。
- `start_review`/`approve`/`reject`: `LearningService`へ状態遷移を委譲する
  （遷移の合法性判定は`LearningService.transition()`自身が行う、ADR-0044〜
  0046・Task11-4）。
- `approve`（`gold_promotion`指定時のみ）: `GoldRepository.add_version()`へ
  更新を委譲する。

SQLite・SQL・Repository具象実装のいずれにも依存しない。`RepositoryError`
（Repository由来）・`LearningServiceError`（`LearningService`由来）は
いずれも捕捉・変換せず、そのまま伝播させる。
"""

from mod_personnel_db.learning import LearningService
from mod_personnel_db.models import GoldRecordId, LearningRecord, LearningRecordId, LearningStatus
from mod_personnel_db.repositories import GoldRepository, LearningRepository
from mod_personnel_db.review import GoldPromotion


class RepositoryReviewService:
    """`LearningRepository`・`GoldRepository`・`LearningService`へ委譲する`ReviewService`実装。"""

    def __init__(
        self,
        learning_repository: LearningRepository,
        gold_repository: GoldRepository,
        learning_service: LearningService,
    ) -> None:
        self._learning_repository = learning_repository
        self._gold_repository = gold_repository
        self._learning_service = learning_service

    def list_pending(self) -> tuple[LearningRecord, ...]:
        return self._learning_repository.list_by_status(LearningStatus.OPEN)

    def start_review(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        return self._learning_service.transition(record_id, LearningStatus.IN_REVIEW, **fields)

    def approve(
        self,
        record_id: LearningRecordId,
        gold_promotion: GoldPromotion | None = None,
        **fields: object,
    ) -> LearningRecord:
        if gold_promotion is not None:
            self._promote_to_gold(gold_promotion)
        return self._learning_service.transition(record_id, LearningStatus.REFLECTED, **fields)

    def reject(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        return self._learning_service.transition(record_id, LearningStatus.WONTFIX, **fields)

    def _promote_to_gold(self, gold_promotion: GoldPromotion) -> GoldRecordId:
        return self._gold_repository.add_version(
            gold_promotion.candidate_id,
            gold_promotion.record,
            gold_promotion.person_key,
            gold_promotion.effective_date,
            gold_promotion.appointment_type,
        )


__all__ = ["RepositoryReviewService"]
