"""Layout Detector関連モデル。docs/api/models.md#layoutdetectionresult, #layoutdefinition に対応。

Version 2.0（ADR-0035, ADR-0036）: Layout Detectorの出力（`LayoutDetectionResult`）と、
判定ルールのみを保持する`LayoutDefinition`を定義する。`layout_id`は`Layout`
（`layouts`テーブル）のDB主キー`LayoutId`ではなく、`LayoutDefinition.era_id`と
同じ値域の`str`である（ADR-0035の補足を参照。Layout Detectorは`repositories/`
に依存しないため、`era_id`からDB主キーへの解決は行わない）。

ADR-0037: `LayoutArtifact`は`LayoutDetector.run()`の戻り値であり、`LayoutDetectionResult`
（`.detection`として格納）に加え、Section Parserに渡す唯一のPDF本文（ページテキスト）を
保持する。
"""

from dataclasses import dataclass
from enum import StrEnum

from mod_personnel_db.models.enums import ConfidenceBand
from mod_personnel_db.models.ids import PdfId
from mod_personnel_db.models.values import ModelValidationError

_SCORE_RANGE = (0.0, 1.0)


class LayoutWarning(StrEnum):
    """Layout Detectorが生成する警告（ADR-0035）。"""

    NO_MATCH = "no_match"
    LOW_CONFIDENCE = "low_confidence"
    AMBIGUOUS_CANDIDATES = "ambiguous_candidates"


class LayoutRuleKind(StrEnum):
    """`LayoutRule.kind`が取り得る判定方法の種別（ADR-0035, ADR-0036）。"""

    HEADER_PATTERN = "header_pattern"
    FOOTER_PATTERN = "footer_pattern"
    MIN_PAGE_COUNT = "min_page_count"
    FONT_NAME_CONTAINS = "font_name_contains"


@dataclass(frozen=True, slots=True)
class LayoutMatch:
    """1つの判定ルールをEvidenceに対して評価した結果。"""

    rule_id: str
    matched: bool
    detail: str | None


@dataclass(frozen=True, slots=True)
class LayoutCandidate:
    """1つの`era_id`（LayoutDefinition）に対する評価結果。"""

    layout_id: str
    score: float
    matched_rules: tuple[LayoutMatch, ...]
    failed_rules: tuple[LayoutMatch, ...]

    def __post_init__(self) -> None:
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class LayoutConfidence:
    """`LayoutDetectionResult.confidence`。共有の`Confidence`とは別の値オブジェクト。"""

    score: float
    band: ConfidenceBand

    def __post_init__(self) -> None:
        if not (_SCORE_RANGE[0] <= self.score <= _SCORE_RANGE[1]):
            raise ModelValidationError(f"score must be within [0.0, 1.0]: {self.score}")


@dataclass(frozen=True, slots=True)
class PageStatistics:
    page_count: int
    average_char_count: float

    def __post_init__(self) -> None:
        if self.page_count < 0:
            raise ModelValidationError("page_count must be >= 0")
        if self.average_char_count < 0:
            raise ModelValidationError("average_char_count must be >= 0")


@dataclass(frozen=True, slots=True)
class BoundingBoxStatistics:
    average_width: float
    average_height: float

    def __post_init__(self) -> None:
        if self.average_width < 0 or self.average_height < 0:
            raise ModelValidationError("average_width/average_height must be >= 0")


@dataclass(frozen=True, slots=True)
class RotationStatistics:
    rotated_page_count: int
    dominant_rotation: int

    def __post_init__(self) -> None:
        if self.rotated_page_count < 0:
            raise ModelValidationError("rotated_page_count must be >= 0")


@dataclass(frozen=True, slots=True)
class LayoutEvidence:
    """Layout Detectorが再読込したPDFから抽出した特徴量。"""

    font_statistics: tuple[str, ...]
    page_statistics: PageStatistics
    bbox_statistics: BoundingBoxStatistics
    rotation_statistics: RotationStatistics
    header_signature: str | None
    footer_signature: str | None
    line_statistics: float
    block_statistics: float

    def __post_init__(self) -> None:
        if self.line_statistics < 0 or self.block_statistics < 0:
            raise ModelValidationError("line_statistics/block_statistics must be >= 0")


@dataclass(frozen=True, slots=True)
class LayoutDetectionResult:
    """Layout Detectorの戻り値（ADR-0035）。"""

    layout_id: str | None
    layout_version: int | None
    confidence: LayoutConfidence
    candidate_layouts: tuple[LayoutCandidate, ...]
    evidence: LayoutEvidence
    warnings: tuple[LayoutWarning, ...]

    def __post_init__(self) -> None:
        if (self.layout_id is None) != (self.layout_version is None):
            raise ModelValidationError("layout_id and layout_version must both be set or unset")
        if self.layout_id is None and not (
            LayoutWarning.NO_MATCH in self.warnings or LayoutWarning.LOW_CONFIDENCE in self.warnings
        ):
            raise ModelValidationError(
                "layout_id is None requires LayoutWarning.NO_MATCH or LOW_CONFIDENCE"
            )


@dataclass(frozen=True, slots=True)
class LayoutRule:
    rule_id: str
    kind: LayoutRuleKind
    value: str
    weight: float

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ModelValidationError("weight must be > 0")


@dataclass(frozen=True, slots=True)
class LayoutDefinition:
    """Layout判定ルールのみを保持する。Knowledgeではない（ADR-0003, ADR-0035）。"""

    era_id: str
    version: int
    rules: tuple[LayoutRule, ...]

    def __post_init__(self) -> None:
        if len(self.rules) == 0:
            raise ModelValidationError("rules must not be empty")
        rule_ids = [rule.rule_id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ModelValidationError("rule_id must be unique within a LayoutDefinition")


@dataclass(frozen=True, slots=True)
class LayoutArtifactPage:
    """`LayoutArtifact.pages`の1ページ分（ADR-0037）。"""

    index: int
    text: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ModelValidationError("index must be >= 0")


@dataclass(frozen=True, slots=True)
class LayoutArtifact:
    """`LayoutDetector.run()`の戻り値（ADR-0037）。

    Section ParserがPDF本文を得る唯一の経路。`detection`はADR-0035が確定した
    `LayoutDetectionResult`（形状は無変更）をそのまま保持する。
    """

    source_pdf_id: PdfId
    detection: LayoutDetectionResult
    pages: tuple[LayoutArtifactPage, ...]

    def __post_init__(self) -> None:
        expected_indices = tuple(range(len(self.pages)))
        actual_indices = tuple(page.index for page in self.pages)
        if actual_indices != expected_indices:
            raise ModelValidationError("pages indices must be a contiguous 0-based sequence")
