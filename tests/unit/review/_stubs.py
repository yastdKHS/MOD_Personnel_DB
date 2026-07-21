"""テスト専用のStub実装群。ReviewServiceの単体テスト用。"""

import dataclasses
from datetime import date, datetime

from mod_personnel_db.models import (
    CandidateId,
    GoldRecord,
    GoldRecordId,
    LearningRecord,
    LearningRecordId,
    LearningStatus,
    NormalizedRecord,
    ParserVersionId,
)
from mod_personnel_db.utils.exceptions import RepositoryError

_VALID_FIELDS = {f.name for f in dataclasses.fields(LearningRecord)}


class StubLearningRepository:
    """LearningRepository Protocolを満たす、メモリ上のdictで代用する最小限のStub。

    未知のフィールド名でRepositoryErrorを送出する点は、実SQLite実装
    （repositories/sqlite/learning.py）の挙動を模す（tests/unit/learning/
    _repository_stub.pyと同じ方針）。
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


class StubGoldRepository:
    """GoldRepository Protocolを満たす、メモリ上のdictで代用する最小限のStub。"""

    def __init__(self) -> None:
        self._records: dict[int, GoldRecord] = {}
        self._next_id = 1
        self.add_version_calls: list[tuple[CandidateId, NormalizedRecord, str, date, str]] = []

    def add_version(
        self,
        candidate_id: CandidateId,
        record: NormalizedRecord,
        person_key: str,
        effective_date: date,
        appointment_type: str,
    ) -> GoldRecordId:
        self.add_version_calls.append(
            (candidate_id, record, person_key, effective_date, appointment_type)
        )
        record_id = GoldRecordId(self._next_id)
        self._next_id += 1
        self._records[int(record_id)] = GoldRecord(
            id=record_id,
            candidate_id=candidate_id,
            person_key=person_key,
            effective_date=effective_date,
            appointment_type=appointment_type,
            fields=record,
            version=1,
            is_current=True,
            superseded_by=None,
        )
        return record_id

    def supersede(self, old_id: GoldRecordId, new_id: GoldRecordId) -> None:
        current = self._records[int(old_id)]
        self._records[int(old_id)] = dataclasses.replace(
            current, is_current=False, superseded_by=new_id
        )

    def get_current(self, person_key: str, effective_date: date) -> GoldRecord | None:
        for record in self._records.values():
            matches = (
                record.person_key == person_key
                and record.effective_date == effective_date
                and record.is_current
            )
            if matches:
                return record
        return None

    def get_history(self, person_key: str) -> tuple[GoldRecord, ...]:
        return tuple(r for r in self._records.values() if r.person_key == person_key)

    def list_current(self, as_of: datetime | None = None) -> tuple[GoldRecord, ...]:
        del as_of
        return tuple(r for r in self._records.values() if r.is_current)
