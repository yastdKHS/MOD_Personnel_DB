"""PDF Registryモデル。docs/api/models.md#pdfrecord に対応する。"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from mod_personnel_db.models.ids import PdfId

PdfStatus = Literal["fetched", "analyzed", "parsed", "validated", "failed"]


@dataclass(frozen=True, slots=True)
class PdfRecord:
    id: PdfId | None
    content_hash: str
    source_url: str
    published_date: date
    fetched_at: datetime
    file_path: str
    file_size_bytes: int
    status: PdfStatus
