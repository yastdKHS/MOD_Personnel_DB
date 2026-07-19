"""Field Extractor関連モデル。docs/api/models.md#fieldextractionresult に対応する（ADR-0038）。

`FieldExtractor.run()`の戻り値（`FieldExtractionResult`）と、行評価の中間結果
（`ExtractionCandidate`/`ExtractionEvidence`/`RawField`）を定義する。永続化対象の
`RawRecord`自体は`models/candidate.py`に定義される（Phase1設計より引き続き使用）。
`RawField.name`は列位置ベースの汎用名（`column_1`, `column_2`, ...）であり、
意味的フィールド名への対応付けは行わない（ADR-0038）。
"""

from dataclasses import dataclass

from mod_personnel_db.models.candidate import RawRecord
from mod_personnel_db.models.values import Confidence, ModelValidationError

_SCORE_RANGE = (0.0, 1.0)


@dataclass(frozen=True, slots=True)
class RawField:
    """1つの列から抽出された生の値。"""

    name: str
    value: str

    def __post_init__(self) -> None:
        if self.name == "":
            raise ModelValidationError("name must not be empty")


@dataclass(frozen=True, slots=True)
class ExtractionEvidence:
    """1行分の列認識の根拠。"""

    line: str
    column_count: int

    def __post_init__(self) -> None:
        if self.column_count < 0:
            raise ModelValidationError("column_count must be >= 0")


@dataclass(frozen=True, slots=True)
class ExtractionCandidate:
    """1行分の評価結果。"""

    record_index: int
    score: float
    fields: tuple[RawField, ...]
    evidence: ExtractionEvidence

    def __post_init__(self) -> None:
        if self.record_index < 0:
            raise ModelValidationError("record_index must be >= 0")
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class FieldExtractionResult:
    """Field Extractorの戻り値（ADR-0038）。"""

    records: tuple[RawRecord, ...]
    candidates: tuple[ExtractionCandidate, ...]
    confidence: Confidence
