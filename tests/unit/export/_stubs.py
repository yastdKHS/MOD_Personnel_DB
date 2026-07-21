"""テスト専用のStub GoldRepository実装。ExportServiceの単体テスト用。"""

from datetime import date, datetime

from mod_personnel_db.models import CandidateId, GoldRecord, GoldRecordId, NormalizedRecord
from mod_personnel_db.utils.exceptions import RepositoryError


class StubGoldRepository:
    """GoldRepository Protocolを満たす、メモリ上のリストで代用する最小限のStub。

    `list_current`/`get_history`への実引数を記録するspyとして機能する
    （実際のas_ofフィルタリングはSQLite実装の責務であり、本Stubの対象外。
    ExportServiceが正しい引数でGoldRepositoryへ委譲することのみを検証する）。
    `raise_on` に一致するメソッド名が呼ばれた場合はRepositoryErrorを送出する。
    """

    def __init__(self, records: tuple[GoldRecord, ...] = (), raise_on: str | None = None) -> None:
        self._records = records
        self._raise_on = raise_on
        self.list_current_calls: list[datetime | None] = []
        self.get_history_calls: list[str] = []

    def _maybe_raise(self, method: str) -> None:
        if self._raise_on == method:
            raise RepositoryError(f"stub failure in {method}")

    def add_version(
        self,
        candidate_id: CandidateId,
        record: NormalizedRecord,
        person_key: str,
        effective_date: date,
        appointment_type: str,
    ) -> GoldRecordId:
        del candidate_id, record, person_key, effective_date, appointment_type
        raise NotImplementedError("ExportService does not call add_version")

    def supersede(self, old_id: GoldRecordId, new_id: GoldRecordId) -> None:
        del old_id, new_id
        raise NotImplementedError("ExportService does not call supersede")

    def get_current(self, person_key: str, effective_date: date) -> GoldRecord | None:
        del person_key, effective_date
        raise NotImplementedError("ExportService does not call get_current")

    def get_history(self, person_key: str) -> tuple[GoldRecord, ...]:
        self.get_history_calls.append(person_key)
        self._maybe_raise("get_history")
        return tuple(r for r in self._records if r.person_key == person_key)

    def list_current(self, as_of: datetime | None = None) -> tuple[GoldRecord, ...]:
        self.list_current_calls.append(as_of)
        self._maybe_raise("list_current")
        return tuple(r for r in self._records if r.is_current)


__all__ = ["StubGoldRepository"]
