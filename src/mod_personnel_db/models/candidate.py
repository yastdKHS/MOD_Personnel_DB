"""候補レコード関連モデル。docs/api/models.md に対応する。"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from mod_personnel_db.models.ids import (
    CandidateId,
    KnowledgeItemId,
    PdfId,
    PersonnelSectionId,
)
from mod_personnel_db.models.values import Confidence, ModelValidationError


@dataclass(frozen=True, slots=True)
class PersonnelSection:
    """Section Parserの出力（ADR-0037）。

    `layout_id`は`Layout`（`layouts`テーブル）のDB主キーではなく、`era_id`
    （`LayoutDetectionResult.layout_id`と同じ値域の`str`）である。Section Parser
    はRepositoryにアクセスしないため、DB主キーへの解決は永続化時にRepository層
    （`SqliteCandidateRepository.add_section`）が担う。
    """

    document_ref: PdfId
    layout_id: str
    section_index: int
    section_label: str | None
    page_range: tuple[int, int]
    section_text: str

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ModelValidationError("section_index must be >= 0")
        start, end = self.page_range
        if start > end:
            raise ModelValidationError("page_range start must be <= end")
        if self.section_text == "":
            raise ModelValidationError("section_text must not be empty")


@dataclass(frozen=True, slots=True)
class RawRecord:
    section_ref: PersonnelSectionId | None
    record_index: int
    raw_fields: Mapping[str, str]
    extracted_at: datetime

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ModelValidationError("record_index must be >= 0")
        if len(self.raw_fields) == 0:
            raise ModelValidationError("raw_fields must not be empty")


@dataclass(frozen=True, slots=True)
class NormalizedValue:
    value: str
    raw: str | None

    def __post_init__(self) -> None:
        if self.value == "":
            raise ModelValidationError("value must not be empty")


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    raw_record_ref: RawRecord
    normalized_fields: Mapping[str, NormalizedValue]
    normalization_applied: tuple[KnowledgeItemId, ...]
    normalized_at: datetime

    def __post_init__(self) -> None:
        if set(self.normalized_fields) != set(self.raw_record_ref.raw_fields):
            raise ModelValidationError(
                "normalized_fields keys must match raw_record_ref.raw_fields keys"
            )
        if self.normalized_at < self.raw_record_ref.extracted_at:
            raise ModelValidationError("normalized_at must be >= raw_record_ref.extracted_at")


@dataclass(frozen=True, slots=True)
class ValidationViolation:
    rule_id: str
    severity: Literal["error", "warning"]
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    subject_ref: NormalizedRecord
    status: Literal["passed", "failed"]
    violations: tuple[ValidationViolation, ...]
    confidence: Confidence
    validated_at: datetime

    def __post_init__(self) -> None:
        has_error = any(v.severity == "error" for v in self.violations)
        if self.status == "failed" and not has_error:
            raise ModelValidationError("status='failed' requires a severity='error' violation")
        if self.status == "passed" and has_error:
            raise ModelValidationError("status='passed' forbids severity='error' violations")


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    id: CandidateId
    section_id: PersonnelSectionId
    raw: RawRecord
    normalized: NormalizedRecord | None
    validation_status: Literal["pending", "passed", "failed"]
