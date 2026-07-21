"""テスト専用のStub LearningRepository実装。RepositoryLearningServiceの単体テスト用。"""

import dataclasses

from mod_personnel_db.models import (
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    ParserVersionId,
)
from mod_personnel_db.utils.exceptions import RepositoryError

_VALID_FIELDS = {f.name for f in dataclasses.fields(LearningRecord)}


class StubLearningRepository:
    """LearningRepository Protocolを満たす、メモリ上のdictで代用する最小限のStub。

    未知のフィールド名でRepositoryErrorを送出する点は、実SQLite実装
    （repositories/sqlite/learning.py）の挙動を模して、RepositoryErrorの
    伝播をテストできるようにするため。
    """

    def __init__(self) -> None:
        self._records: dict[int, LearningRecord] = {}
        self._next_id = 1

    def add(self, record: LearningRecord) -> LearningRecordId:
        record_id = LearningRecordId(self._next_id)
        self._next_id += 1
        self._records[int(record_id)] = dataclasses.replace(record, id=record_id)
        return record_id

    def update(self, record_id: LearningRecordId, **fields: object) -> LearningRecord:
        if int(record_id) not in self._records:
            raise RepositoryError(f"learning_dataset.id={record_id} not found")
        unknown = set(fields) - _VALID_FIELDS
        if unknown:
            raise RepositoryError(f"unknown LearningRecord field: {sorted(unknown)!r}")
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
