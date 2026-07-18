"""Reviewモデル（簡略版）。docs/api/models.md#reviewitem に対応する。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from mod_personnel_db.models.ids import CandidateId, GoldRecordId, ReviewSessionId
from mod_personnel_db.models.values import ModelValidationError

ReviewTargetTable = Literal["candidate_records", "gold_records"]


@dataclass(frozen=True, slots=True)
class ReviewItem:
    session_id: ReviewSessionId
    target_table: ReviewTargetTable
    target_id: CandidateId | GoldRecordId
    field_name: str
    old_value: str | None
    new_value: str
    change_reason: str | None
    reviewer: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.new_value == self.old_value:
            raise ModelValidationError("new_value must differ from old_value")
        if self.reviewer == "":
            raise ModelValidationError("reviewer must not be empty")
