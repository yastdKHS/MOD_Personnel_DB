"""Document Analyzer出力モデル。docs/api/models.md#document に対応する。"""

from dataclasses import dataclass
from datetime import datetime

from mod_personnel_db.models.ids import PdfId
from mod_personnel_db.models.values import ModelValidationError


@dataclass(frozen=True, slots=True)
class Page:
    index: int
    text: str
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ModelValidationError("index must be >= 0")
        if self.width <= 0 or self.height <= 0:
            raise ModelValidationError("width/height must be positive")


@dataclass(frozen=True, slots=True)
class Document:
    source_pdf_id: PdfId
    pages: tuple[Page, ...]
    analyzed_at: datetime

    def __post_init__(self) -> None:
        if len(self.pages) == 0:
            raise ModelValidationError("pages must not be empty")
        expected_indices = tuple(range(len(self.pages)))
        actual_indices = tuple(page.index for page in self.pages)
        if actual_indices != expected_indices:
            raise ModelValidationError("page indices must be a contiguous 0-based sequence")
