"""テスト専用のStub LearningService実装。具象実装はsrc/には置かない（Phase3 Task10-0.2）。"""

import dataclasses

from mod_personnel_db.models import LearningRecord, LearningRecordId, LearningStatus


class StubLearningService:
    """LearningService Protocolを満たす、メモリ上のリストで代用する最小限のStub。"""

    def __init__(self) -> None:
        self._records: dict[int, LearningRecord] = {}
        self._next_id = 1

    def record_error(self, entry: LearningRecord) -> LearningRecordId:
        record_id = LearningRecordId(self._next_id)
        self._next_id += 1
        self._records[int(record_id)] = entry
        return record_id

    def transition(
        self, record_id: LearningRecordId, new_status: LearningStatus, **fields: object
    ) -> LearningRecord:
        current = self._records[int(record_id)]
        updated = dataclasses.replace(current, status=new_status, **fields)  # type: ignore[arg-type]
        self._records[int(record_id)] = updated
        return updated

    def list_open(self) -> tuple[LearningRecord, ...]:
        return tuple(
            record for record in self._records.values() if record.status == LearningStatus.OPEN
        )

    def summarize_by_error_category(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for record in self._records.values():
            key = str(record.error_category)
            summary[key] = summary.get(key, 0) + 1
        return summary
