"""LearningService契約（Protocol）。docs/api/interfaces.md#learningservice に対応する。

Phase3 Task10-0.2（契約整備のみ）の対象。Dependency Injection用の抽象型のみを
提供し、LearningRepositoryへの永続化を伴う具象実装は含まない（具象実装は
将来のタスクでlearning/配下に追加する、docs/api/package-design.mdのlearning/節）。
"""

from typing import Protocol

from mod_personnel_db.models import LearningRecord, LearningRecordId, LearningStatus


class LearningService(Protocol):
    """Learning Dataset（ADR-0013, ADR-0017）のライフサイクルを管理する。"""

    def record_error(self, entry: LearningRecord) -> LearningRecordId: ...

    def transition(
        self, record_id: LearningRecordId, new_status: LearningStatus, **fields: object
    ) -> LearningRecord:
        """状態遷移（open→in_review→reflected→verified/wontfix）を1段階進める。"""
        ...

    def list_open(self) -> tuple[LearningRecord, ...]: ...

    def summarize_by_error_category(self) -> dict[str, int]: ...


__all__ = ["LearningService"]
