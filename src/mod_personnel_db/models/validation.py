"""Validator関連モデル。docs/api/models.md#validationresult に対応する（ADR-0043）。

`Validator.run()`の戻り値（`ValidationResult`）と、レコード評価の中間結果
（`ValidationCandidate`/`ValidationEvidence`/`ValidationError`/`ValidationWarning`）
を定義する。`FieldExtractionResult`（ADR-0038）・`NormalizationResult`
（ADR-0040）と同型の集約結果パターン。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from mod_personnel_db.models.values import Confidence, ModelValidationError

_SCORE_RANGE = (0.0, 1.0)


@dataclass(frozen=True, slots=True)
class ValidationError:
    """1件のValidation Rule違反（severity=error相当）。"""

    rule_id: str
    message: str

    def __post_init__(self) -> None:
        if self.rule_id == "":
            raise ModelValidationError("rule_id must not be empty")
        if self.message == "":
            raise ModelValidationError("message must not be empty")


@dataclass(frozen=True, slots=True)
class ValidationWarning:
    """1件のValidation Rule違反（severity=warning相当）。"""

    rule_id: str
    message: str

    def __post_init__(self) -> None:
        if self.rule_id == "":
            raise ModelValidationError("rule_id must not be empty")
        if self.message == "":
            raise ModelValidationError("message must not be empty")


@dataclass(frozen=True, slots=True)
class ValidationEvidence:
    """1レコード分の検証の根拠。"""

    record_index: int
    layout_id: str
    rules_evaluated: int

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ModelValidationError("record_index must be >= 0")
        if self.layout_id == "":
            raise ModelValidationError("layout_id must not be empty")
        if self.rules_evaluated < 0:
            raise ModelValidationError("rules_evaluated must be >= 0")


@dataclass(frozen=True, slots=True)
class ValidationCandidate:
    """1レコード分の評価結果。"""

    record_index: int
    score: float
    errors: tuple[ValidationError, ...]
    warnings: tuple[ValidationWarning, ...]
    evidence: ValidationEvidence

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ModelValidationError("record_index must be >= 0")
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Validatorの戻り値（ADR-0043）。レコードの値は含まない。"""

    status: Literal["passed", "failed"]
    candidates: tuple[ValidationCandidate, ...]
    confidence: Confidence
    validated_at: datetime

    def __post_init__(self) -> None:
        has_error = any(candidate.errors for candidate in self.candidates)
        if self.status == "failed" and not has_error:
            raise ModelValidationError("status='failed' requires at least one ValidationError")
        if self.status == "passed" and has_error:
            raise ModelValidationError("status='passed' forbids ValidationError")
