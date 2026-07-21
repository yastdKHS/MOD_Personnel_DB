"""ReviewService契約（Protocol）。docs/adr/0021-review-ui-strategy.mdに対応する。

Learning Dataset（`learning_dataset`、ADR-0013/0017）に蓄積されたエントリを
人間がレビューし、承認（Gold反映）または却下（対応不要）を確定するための、
最小限のReview機能の契約を定める（Phase4 Task12-0）。

`docs/api/review.md`・`docs/review/`が定めるより広範な
（CandidateRecord/GoldRecordのレビューセッション・キュー管理・割当・
差戻し等を含む）`ReviewService`とは異なる、Learning Dataset固有の
レビュー契約である。両者の統合・命名の整理は将来のADRに委ねる
（詳細はPhase4 Task12-0 Review Reportを参照）。

具象実装（`RepositoryReviewService`）は`mod_personnel_db.review.service`
から直接importする。本ファイルからは再エクスポートしない。`service.py`は
本ファイルが定義する`GoldPromotion`をimportするため、ここで`service.py`を
importすると循環参照になる（`pipeline/__init__.py`と`pipeline/job_runner.py`
の関係と同じ理由。詳細は`pipeline/__init__.py`のコメントを参照）。
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from mod_personnel_db.models import (
    CandidateId,
    LearningRecord,
    LearningRecordId,
    NormalizedRecord,
)


@dataclass(frozen=True, slots=True)
class GoldPromotion:
    """`approve()`が`GoldRepository.add_version()`へそのまま渡す内容。

    値の組み立ては呼び出し元（レビュー担当者側のUI/CLI等）の責務であり、
    `ReviewService`自身はCandidateRecordから値を導出しない。
    """

    candidate_id: CandidateId
    record: NormalizedRecord
    person_key: str
    effective_date: date
    appointment_type: str


class ReviewService(Protocol):
    """Learning Datasetエントリの人手レビュー（ADR-0021）を仲介する。"""

    def list_pending(self) -> tuple[LearningRecord, ...]:
        """レビュー待ち（`status='open'`）のLearning Datasetエントリを返す。"""
        ...

    def start_review(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        """レビューに着手する（`open` → `in_review`）。"""
        ...

    def approve(
        self,
        record_id: LearningRecordId,
        gold_promotion: GoldPromotion | None = None,
        **fields: object,
    ) -> LearningRecord:
        """レビューを承認する（`in_review` → `reflected`）。`gold_promotion`を
        指定した場合のみGoldRepositoryへの反映を委譲する。"""
        ...

    def reject(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        """レビューを却下する（`in_review` → `wontfix`）。"""
        ...


__all__ = ["GoldPromotion", "ReviewService"]
