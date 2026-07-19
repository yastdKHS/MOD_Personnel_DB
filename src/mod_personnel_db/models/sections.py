"""Section Parser関連モデル。docs/api/models.md#sectionparseresult に対応する（ADR-0037）。

Section Parserの正式な出力単位（永続化対象）は`models/candidate.py`の
`PersonnelSection`（Phase1設計より引き続き使用）。本モジュールは、Section境界
判定の過程で生じる中間評価（`SectionCandidate`/`SectionEvidence`）と、
`SectionParser.run()`が返す集約結果（`SectionParseResult`）を定義する。
"""

from dataclasses import dataclass

from mod_personnel_db.models.candidate import PersonnelSection
from mod_personnel_db.models.values import Confidence, ModelValidationError

_SCORE_RANGE = (0.0, 1.0)


@dataclass(frozen=True, slots=True)
class SectionEvidence:
    """1つのSection境界候補の根拠（Header/Body/Footer判定の結果）。"""

    header_line: str | None
    footer_line: str | None
    body_line_count: int
    page_range: tuple[int, int]

    def __post_init__(self) -> None:
        if self.body_line_count < 0:
            raise ModelValidationError("body_line_count must be >= 0")
        start, end = self.page_range
        if start > end:
            raise ModelValidationError("page_range start must be <= end")


@dataclass(frozen=True, slots=True)
class SectionCandidate:
    """1つのSection境界候補の評価結果。"""

    section_index: int
    score: float
    evidence: SectionEvidence

    def __post_init__(self) -> None:
        if self.section_index < 0:
            raise ModelValidationError("section_index must be >= 0")
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class SectionParseResult:
    """Section Parserの戻り値（ADR-0037）。"""

    sections: tuple[PersonnelSection, ...]
    candidates: tuple[SectionCandidate, ...]
    confidence: Confidence
