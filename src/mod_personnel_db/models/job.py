"""ジョブ・Parserバージョンモデル。docs/api/models.md#job, #parserversion に対応する。"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from mod_personnel_db.models.ids import JobId, ParserVersionId, PdfId
from mod_personnel_db.models.values import ModelValidationError

JobType = Literal["fetch", "core_pipeline", "export", "backfill", "knowledge_reload"]
JobStatus = Literal["running", "succeeded", "failed"]

_CODE_VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")


@dataclass(frozen=True, slots=True)
class Job:
    id: JobId | None
    job_type: JobType
    pdf_id: PdfId | None
    parser_version_id: ParserVersionId | None
    status: JobStatus
    started_at: datetime
    finished_at: datetime | None
    processed_count: int
    failed_count: int
    error_summary: str | None

    def __post_init__(self) -> None:
        if self.status == "running" and self.finished_at is not None:
            raise ModelValidationError("status='running' requires finished_at is None")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ModelValidationError("finished_at must be >= started_at")
        if self.processed_count < 0 or self.failed_count < 0:
            raise ModelValidationError("processed_count/failed_count must be >= 0")


@dataclass(frozen=True, slots=True)
class ParserVersion:
    id: ParserVersionId | None
    code_version: str
    knowledge_snapshot_checksum: str
    released_at: datetime
    notes: str | None

    def __post_init__(self) -> None:
        if not _CODE_VERSION_PATTERN.match(self.code_version):
            raise ModelValidationError(
                f"code_version must match ^v\\d+\\.\\d+\\.\\d+$: {self.code_version}"
            )
