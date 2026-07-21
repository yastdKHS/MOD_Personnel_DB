"""LearningService契約（Protocol）と具象実装。docs/api/interfaces.md#learningservice に対応する。

Dependency Injection用の抽象型（`LearningService` Protocol）に加え、
`LearningRepository`へ永続化を委譲するライフサイクル管理の具象実装
（`RepositoryLearningService`）を提供する（docs/api/package-design.mdの
learning/節）。具象実装の生成はComposition Root（`cli/`、ADR-0046）にのみ
許可される。
"""

from typing import Protocol

from mod_personnel_db.learning.service import RepositoryLearningService
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


__all__ = ["LearningService", "RepositoryLearningService"]
