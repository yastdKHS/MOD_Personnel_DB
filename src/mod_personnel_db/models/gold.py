"""Gold Database読み取りビュー。docs/api/models.md#goldrecord に対応する。"""

from dataclasses import dataclass
from datetime import date

from mod_personnel_db.models.candidate import NormalizedRecord
from mod_personnel_db.models.ids import CandidateId, GoldRecordId


@dataclass(frozen=True, slots=True)
class GoldRecord:
    id: GoldRecordId
    candidate_id: CandidateId
    person_key: str
    effective_date: date
    appointment_type: str
    fields: NormalizedRecord
    version: int
    is_current: bool
    superseded_by: GoldRecordId | None
