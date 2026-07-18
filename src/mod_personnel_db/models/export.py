"""公開エクスポート記録モデル。docs/api/models.md#exportrecord に対応する。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from mod_personnel_db.models.ids import ExportId
from mod_personnel_db.models.values import ModelValidationError

ExportFormat = Literal["csv", "parquet", "json"]
ExportStatus = Literal["completed", "failed"]


@dataclass(frozen=True, slots=True)
class ExportRecord:
    id: ExportId | None
    format: ExportFormat
    destination: str
    as_of: datetime
    record_count: int
    checksum: str
    status: ExportStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if self.record_count < 0:
            raise ModelValidationError("record_count must be >= 0")
        if self.status == "completed" and self.checksum == "":
            raise ModelValidationError("checksum must not be empty when status='completed'")
